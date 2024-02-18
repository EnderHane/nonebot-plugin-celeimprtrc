import os

if not os.getenv('NONEBOT_PLUGIN_CELEIMPRTRC_DEV'):
    from typing import Annotated

    from nonebot import on_command, on_keyword, logger
    from nonebot.adapters import Message
    from nonebot.params import CommandArg
    from nonebot.adapters.satori import Bot as SatoriBot
    from nonebot.adapters.satori.event import MessageEvent as SatoriMessageEvent
    from nonebot.adapters.satori.event import PublicMessageEvent as SatoriPublicMessageEvent
    from nonebot.adapters.satori.message import MessageSegment as SatoriMessageSegment, Message as SatoriMessage
    from nonebot.adapters.satori.models import ChannelType

    from .config import config as plugin_config
    from .data import satori_listening_data
    from .github import check_repo_path, check_file_name_on_whitelist, upload_to_repo
    from .format import check_format_error, make_message
    from .download import download_with_size_limit

    help_msg = 'usage: /impr_trc.reg github <Owner> <Repo> [Path]'

    auth_tip_msg = [
        SatoriMessageSegment.text('Cannot auth for Github App.'),
        SatoriMessageSegment.br(),
        SatoriMessageSegment.text(
            f'Please confirm the app {plugin_config.github.app_info.app_name} is installed to the repo '),
        SatoriMessageSegment.text('and the path does exist.'),
        SatoriMessageSegment.link_button(
            plugin_config.github.app_info.app_website, 'App Website'),
    ]


    async def is_public_text(event: SatoriMessageEvent) -> bool:
        return event.channel.type == ChannelType.TEXT


    reg_command_matcher = on_command(('impr_trc', 'reg'), rule=is_public_text)
    unreg_command_matcher = on_command(('impr_trc', 'unreg'), rule=is_public_text)

    file_matcher = on_keyword({'file'}, rule=is_public_text)


    def get_area(event: SatoriPublicMessageEvent) -> str:
        listening_area = event.platform
        if event.guild:
            listening_area += '/' + event.guild.id
        if event.channel:
            listening_area += '/' + event.channel.id
        return listening_area


    def get_single_file(event: SatoriPublicMessageEvent) -> (str, str):
        tree = event.message.content

        from nonebot.adapters.satori.utils import Element

        def _try_get_file(tr: Element) -> (str, str):
            if tr.type == 'file':
                title = tr.attrs.get('title')
                src = tr.attrs.get('src')
                if title and src:
                    return title, src
                else:
                    logger.debug(f'Found file in message {event.message.id} but cannot extract the information.')
            for el1 in tr.children:
                r1 = _try_get_file(el1)
                if r1:
                    return r1

        for el in tree:
            r = _try_get_file(el)
            if r:
                return r


    @reg_command_matcher.handle()
    async def impr_trc_reg(bot: SatoriBot, args: Annotated[Message, CommandArg()], event: SatoriPublicMessageEvent):
        argv = [a for a in args.extract_plain_text().split() if a]
        match n := len(argv):
            case 3 | 4:
                path = argv[3] if n > 3 else ''
                host, owner, repo, *_ = argv[:]
                if host != 'github':
                    await bot.send(event, SatoriMessageSegment.text('Only Github is supported.'))
                    return
                auth_suc, is_path = await check_repo_path(owner, repo, path)
                if not all((auth_suc, is_path)):
                    logger.trace(
                        f'Cannot auth for Github App {plugin_config.github.app_info.app_name} on {owner}/{repo}/{path}')
                    await reg_fail_no_auth(bot, event)
                    return
                listening_area = get_area(event)
                host_list = satori_listening_data[listening_area] or []
                satori_listening_data[listening_area] = host_list + [
                    {'host': host, 'owner': owner, 'repo': repo, 'path': path}]
                full_repo = f'{host}/{owner}/{repo}/{path}'
                await reg_success(bot, event, full_repo)
            case _:
                await reg_ignored_invalid_command(bot, event)


    async def reg_success(bot, event, full_repo):
        await bot.send(event, SatoriMessageSegment.text(f'Listening for {full_repo}'))
        await bot.reaction_create(channel_id=event.channel.id, message_id=event.message.id, emoji='➕')


    async def reg_fail_no_auth(bot, event):
        await bot.send(event, SatoriMessage(auth_tip_msg))
        await bot.reaction_create(channel_id=event.channel.id, message_id=event.message.id, emoji='🔧')


    async def reg_ignored_invalid_command(bot, event):
        await bot.send(event, SatoriMessageSegment.text(help_msg))
        await bot.reaction_create(channel_id=event.channel.id, message_id=event.message.id, emoji='❓')


    @unreg_command_matcher.handle()
    async def impr_trc_unreg(bot: SatoriBot, event: SatoriPublicMessageEvent):
        listening_area = get_area(event)
        if listening_area in satori_listening_data:
            del satori_listening_data[listening_area]
            await unreg_success(bot, event)
        else:
            await unreg_ignored(bot, event)


    async def unreg_success(bot, event):
        await bot.send(event, SatoriMessageSegment.text('Unregistered successfully'))
        await bot.reaction_create(channel_id=event.channel.id, message_id=event.message.id, emoji='👌')


    async def unreg_ignored(bot, event):
        await bot.send(event, SatoriMessageSegment.text('Not listening'))
        await bot.reaction_create(channel_id=event.channel.id, message_id=event.message.id, emoji='✋')


    @file_matcher.handle()
    async def file_handle(bot: SatoriBot, event: SatoriPublicMessageEvent):
        area = get_area(event)
        ld = satori_listening_data[area]
        if not ld:
            return
        file_info = get_single_file(event)
        if not file_info:
            return
        title, src = file_info
        file_raw = await download_with_size_limit(src)
        if not file_raw:
            await file_ignored_too_large(bot, event)
            return
        file_content = file_raw.decode()
        errors = check_format_error(file_content)
        if errors:
            await file_denied_invalid_format(bot, errors, event)
            return
        for h in ld:
            owner = h['owner']
            repo = h['repo']
            path = h['path']
            can_upload = await check_file_name_on_whitelist(owner, repo, path, title, file_content)
            if can_upload:
                t, display, gh, old = can_upload
                old_content, old_sha = old or (None, None)
                message = make_message(f'{event.user.name}({event.user.id}@{event.platform})', display, file_content,
                                       old_content)

                await upload_to_repo(gh, owner, repo, f'{path}/{t}', file_content, message, old_sha)
                await file_uploaded(bot, event)


    async def file_uploaded(bot, event):
        await bot.reaction_create(channel_id=event.channel.id, message_id=event.message.id, emoji='✏️')


    async def file_ignored_too_large(bot, event):
        await bot.reaction_create(channel_id=event.channel.id, message_id=event.message.id, emoji='🐡')


    async def file_denied_invalid_format(bot, errors, event):
        message = SatoriMessageSegment.quote(event.message.id)
        for e in errors:
            message += SatoriMessageSegment.br()
            message += SatoriMessageSegment.text(e)
        await bot.send(event, message)
        await bot.reaction_create(channel_id=event.channel.id, message_id=event.message.id, emoji='💢')

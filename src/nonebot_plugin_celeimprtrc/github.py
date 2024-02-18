import os
from typing import Annotated

if not os.getenv('NONEBOT_PLUGIN_CELEIMPRTRC_DEV'):

    from githubkit import GitHub, AppAuthStrategy
    from githubkit.exception import GitHubException

    import tomllib
    import base64

    from .config import config as plugin_config

    try:
        auth = AppAuthStrategy(plugin_config.github.app_id.get_secret_value(),
                               plugin_config.github.private_key.get_secret_value())
        gh = GitHub(auth)
        gh.rest.apps.get_authenticated()
    except GitHubException as e:
        print('GitHub App authentication failed!')
        raise


    def valid_path(p: str) -> str:
        return '/'.join({com for com in p.split('/') if com})


    async def check_repo_path(owner: str, repo: str, path: str) -> (bool, bool):
        path = valid_path(path)
        try:
            inst = (await gh.rest.apps.async_get_repo_installation(owner, repo)).parsed_data
            inst_gh = gh.with_auth(gh.auth.as_installation(inst.id))
            contents = (await inst_gh.rest.repos.async_get_content(owner, repo, path)).parsed_data
            if isinstance(contents, list):
                return True, True
            else:
                return True, False
        except GitHubException:
            return False, False
        except Exception:
            return False, False


    async def check_file_name_on_whitelist(owner: str, repo: str, path: str, file_title: str,
                                           file_content: str) -> (
            Annotated[str, 'file title'], Annotated[str, 'display name'], GitHub,
            Annotated[tuple[str, str], 'old file content and sha']):
        path = valid_path(path)
        inst = (await gh.rest.apps.async_get_repo_installation(owner, repo)).parsed_data
        inst_gh = gh.with_auth(gh.auth.as_installation(inst.id))
        contents = (await inst_gh.rest.repos.async_get_content(owner, repo, path)).parsed_data
        files = [f for f in contents if f.type == 'file']
        title = file_title
        display_name = file_title
        old_file_content = None
        for f in files:
            if f.name == '.imprtrc-whitelisted.toml':
                whl = (await inst_gh.rest.repos.async_get_content(owner, repo, f.path)).parsed_data
                whl_dict = tomllib.loads(base64.b64decode(whl.content).decode())
                for k in whl_dict:
                    if whl_dict[k]['map_path'] in file_content:
                        title, display_name = k, whl_dict[k]['display_name']
                        break
                else:
                    return None
        for f in files:
            if f.name == title:
                old_file = (await inst_gh.rest.repos.async_get_content(owner, repo, f.path)).parsed_data
                old_file_content = (base64.b64decode(old_file.content).decode(), old_file.sha)
        return title, display_name, inst_gh, old_file_content


    async def upload_to_repo(inst_gh: GitHub, owner: str, repo: str, file_full_path: str,
                             file_content: str, message: str, sha: str | None):
        path = valid_path(file_full_path)
        if sha:
            await inst_gh.rest.repos.async_create_or_update_file_contents(owner, repo, path,
                                                                          content=base64.b64encode(
                                                                              file_content.encode()),
                                                                          message=message, sha=sha)
        else:
            await inst_gh.rest.repos.async_create_or_update_file_contents(owner, repo, path,
                                                                          content=base64.b64encode(
                                                                              file_content.encode()),
                                                                          message=message)

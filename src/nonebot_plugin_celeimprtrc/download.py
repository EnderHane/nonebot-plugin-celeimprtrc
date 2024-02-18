import os

if not os.getenv('NONEBOT_PLUGIN_CELEIMPRTRC_DEV'):
    import httpx

    from .config import config as plugin_config


    async def download_with_size_limit(src: str) -> bytes | None:
        async def is_eof(it):
            try:
                await anext(it)
            except StopAsyncIteration:
                return True
            return False

        async with httpx.AsyncClient() as client:
            async with client.stream('GET', src) as r:
                aitr = r.aiter_bytes(plugin_config.max_file_size_kib * 1024)
                file_content: bytes = await anext(aitr)
                if not await is_eof(aitr):
                    return None
        return file_content

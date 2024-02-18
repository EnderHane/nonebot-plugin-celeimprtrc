import os

if not os.getenv('NONEBOT_PLUGIN_CELEIMPRTRC_DEV'):
    import re

    time_pat = re.compile(r'[0-9.:]+\((\d+)\)')


    def make_message(user: str, display_name: str, new_content: str, old_content: str | None = None) -> str:
        verb = 'update'
        if old_content:
            old_time = get_time(old_content)
            new_time = get_time(new_content)
            if old_time and new_time:
                dt = int(old_time) - int(new_time)
                verb = f'{-dt}f'
        disp_time = get_display_time(new_content) or ''
        return f'{user} {verb} {display_name} {disp_time}'.rstrip()


    def get_time(tas_content: str) -> str | None:
        m = time_pat.search(tas_content)
        if m:
            return m.group(1)


    def get_display_time(tas_content: str) -> str | None:
        m = time_pat.search(tas_content)
        if m:
            return m.group(0)


    def check_format_error(tas_content: str) -> list[str]:
        errors = []
        breakpoints = []
        timestamps = []
        start_labels = []
        for i, line in enumerate(tas_content.splitlines()):
            if '***' in line:
                breakpoints += [i + 1]
            if time_pat.search(line):
                timestamps += [i + 1]
            if line.startswith('#Start'):
                start_labels += [i + 1]
        if breakpoints:
            breakpoint_msg = 'breakpoints at line'
            for i in breakpoints:
                breakpoint_msg += f' {i},'
            breakpoint_msg.removesuffix(',')
            errors += [breakpoint_msg]
        if not timestamps:
            errors += [f'no timestamp']
        if len(timestamps) > 1:
            time_stamp_msg = 'too many timestamps at line'
            for i in timestamps:
                time_stamp_msg += f' {i},'
            time_stamp_msg.removesuffix(',')
            errors += [time_stamp_msg]
        if not start_labels:
            errors += ['no #Start label']
        if len(start_labels) > 1:
            start_label_msg = 'too many #Start label at line'
            for i in start_labels:
                start_label_msg += f' {i},'
            start_label_msg.removesuffix(',')
            errors += [start_label_msg]
        return errors

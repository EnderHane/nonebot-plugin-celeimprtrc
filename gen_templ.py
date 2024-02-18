import tomli_w

import re
from jsf import JSF
from nonebot_plugin_celeimprtrc.config import Config, plugin_root

quote_pat = re.compile(r'".*?"')
num_pat = re.compile(r'\d+')

templ_path = plugin_root / 'config.template.toml'

tom = tomli_w.dumps(JSF(Config.schema()).generate())
tom = re.sub(quote_pat, r'""', tom)
tom = re.sub(num_pat, r'0', tom)
print(tom)
templ_path.write_text(tom)

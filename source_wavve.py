import re
from pathlib import Path
from urllib.parse import quote

import requests

from support import SupportSC

# local
from .model import ChannelItem
from .setup import P, default_headers
from .source_base import SourceBase

logger = P.logger
package_name = P.package_name
ModelSetting = P.ModelSetting


def load_support_module():
    if Path(__file__).parent.joinpath("wavve.py").is_file():
        from . import wavve as Wavve

        return Wavve
    return SupportSC.load_module_f(__file__, "wavve")


class SourceWavve(SourceBase):
    source_name = "wavve"
    mod = None

    @classmethod
    def prepare(cls, *args, **kwargs):
        if cls.mod is not None:
            return
        try:
            cls.mod = load_support_module()
        except (ImportError, ModuleNotFoundError):
            logger.error("support site 플러그인이 필요합니다.")
        except Exception:
            logger.exception("Support Module 로딩 중 예외:")

    @classmethod
    def get_channel_list(cls):
        ret = []
        data = cls.mod.live_all_channels()
        for item in data["list"]:
            img = "https://" + item["tvimage"] if item["tvimage"] != "" else ""
            c = ChannelItem(
                cls.source_name, item["channelid"], item["channelname"], quote(img), item["type"] == "video"
            )
            c.current = item["title"]
            ret.append(c)
        return ret

    @classmethod
    def get_url(cls, channel_id, mode, quality=None):
        surl = None
        data = cls.mod.streaming("live", channel_id, quality)
        if data is not None and "playurl" in data:
            surl = data["playurl"]
            # 2022-01-10 라디오. 대충 함
            # if data['quality'] == '100p' or data['qualities']['list'][0]['name'] == '오디오모드':
            #    surl = data['playurl'].replace('/100/100', '/100') + f"/live.m3u8{data['debug']['orgurl'].split('.m3u8')[1]}"
        if surl is None:
            raise ValueError("URL is None")
        if mode == "web_play":
            return "return_after_read", surl
        if ModelSetting.get("wavve_streaming_type") == "redirect":
            return "redirect", surl
        return "return_after_read", surl

    @classmethod
    def get_return_data(cls, url, mode=None):
        while True:
            data = requests.get(url, proxies=cls.mod.get_proxies(), headers=default_headers, timeout=30).text
            prefix = url.split("?")[0].rsplit("/", 1)[0]
            if re.findall(r"\.m3u8\?", data):
                url = prefix + "/" + data.strip().split("\n")[-1]
            else:
                break
        new_data = ""
        for line in data.split("\n"):
            line = line.strip()
            if line.startswith != "#" and ".ts?" in line:
                line = f"{prefix}/{line}"
            new_data += f"{line}\n"
        if ModelSetting.get("wavve_streaming_type") == "direct":
            return new_data
        ret = cls.change_redirect_data(new_data, proxy=cls.mod.get_proxy())
        return ret
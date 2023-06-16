import re

import requests

# local
from .model import ChannelItem, SimpleItem
from .setup import P, default_headers
from .source_base import SourceBase

logger = P.logger
package_name = P.package_name
ModelSetting = P.ModelSetting


class SourceNavertv(SourceBase):
    source_name = "navertv"

    @classmethod
    def get_channel_list(cls):
        ret = []
        cls.channel_cache = {}
        for item in map(str.strip, ModelSetting.get(f"{cls.source_name}_list").splitlines()):
            if not item:
                continue
            tmp = item.split("|")
            if len(tmp) == 3:
                cid, title, url = tmp
                quality = "1080"
            elif len(tmp) == 4:
                cid, title, url, quality = tmp
            else:
                continue
            c = ChannelItem(cls.source_name, cid, title, None, True)
            cls.channel_cache[cid] = SimpleItem(cid, title, url, quality)
            ret.append(c)
        return ret

    @classmethod
    def __get_url(cls, target_url, quality):
        if target_url.startswith("SPORTS_"):
            target_ch = target_url.split("_")[1]
            if not target_ch.startswith("ad") and not target_ch.startswith("ch"):
                target_ch = "ch" + target_ch
            tmp = {"480": "800", "720": "2000", "1080": "5000"}
            qua = tmp.get(quality, "5000")
            tmp = f"https://apis.naver.com/pcLive/livePlatform/sUrl?ch={target_ch}&q={qua}&p=hls&cc=KR&env=pc"
            url = requests.get(tmp, headers=default_headers, timeout=30).json()["secUrl"]

            # https://proxy-gateway.sports.naver.com/livecloud/lives/3278079/playback?countryCode=KR&devt=HTML5_PC&timeMachine=true&p2p=true&includeThumbnail=true&pollingStatus=true
        else:
            # logger.debug(target_url)
            text = requests.get(target_url, headers=default_headers, timeout=30).text
            match = re.search(r"liveId: \'(?P<liveid>\d+)\'", text)
            # logger.debug(match)
            if match:
                liveid = match.group("liveid")
                # https://api.tv.naver.com/api/open/live/v2/player/playback?liveId=3077128&countryCode=KR&timeMachine=true
                json_url = f"https://api.tv.naver.com/api/open/live/v2/player/playback?liveId={liveid}&countryCode=KR&timeMachine=true"
                data = requests.get(json_url, headers=default_headers, timeout=30).json()

                url = data["media"][0]["path"]
        return url

    @classmethod
    def get_url(cls, channel_id, mode, quality=None):
        # logger.debug('channel_id:%s, quality:%s, mode:%s', channel_id, quality, mode)
        target_url = cls.channel_cache[channel_id].url
        url = cls.__get_url(target_url, cls.channel_cache[channel_id].quality)
        if mode == "web_play":
            return "return_after_read", url
        return "redirect", url
from datetime import datetime, timedelta
import os
from urllib.parse import parse_qs, urlparse

from tool import ToolUtil
from flask import Response
from .setup import *
from .model import ModelPktvItem

try:
    if os.path.exists(os.path.join(os.path.dirname(__file__), "source_pktv_handler.py")):
        from .source_pktv_handler import PKTV_Handler

    else:
        from support import SupportSC

        PKTV_Handler = SupportSC.load_module_f(__file__, "source_pktv_handler").PKTV_Handler
except:
    pass


class ModuleMain(PluginModuleBase):
    def __init__(self, P):
        super(ModuleMain, self).__init__(P, name="main", first_menu="setting", scheduler_desc="판다라이브")
        self.db_default = {
            f"{self.name}_db_version": "1",
            f"{self.name}_auto_start": "False",
            f"{self.name}_interval": "5",
            f"{self.name}_db_delete_day": "3",
            f"{self.name}_db_auto_delete": "False",
            "plex_server_url": "http://localhost:32400",
            "plex_token": "",
            "plex_meta_item": "",
            "yaml_path": "",
            "use_quality": "1920x1080",
            "streaming_type": "redirect",
            "username": "",
            "password": "",
            "token_refresh_hour": "5",
            "token": "",
            "token_time": "",
            "use_proxy": "False",
            "use_proxy2": "False",
            "proxy_url": "",
        }
        self.web_list_model = ModelPktvItem

    def process_menu(self, sub, req):
        arg = P.ModelSetting.to_dict()
        arg["api_m3u"] = ToolUtil.make_apikey_url(f"/{P.package_name}/api/m3u")
        arg["api_playlist"] = ToolUtil.make_apikey_url(f"/{P.package_name}/api/playlist")
        arg["api_yaml"] = ToolUtil.make_apikey_url(f"/{P.package_name}/api/yaml")
        arg["hls_playback"] = "https://chrome.google.com/webstore/detail/native-hls-playback/emnphkkblegpebimobpbekeedfgemhof"
        if sub == "setting":
            arg["is_include"] = F.scheduler.is_include(self.get_scheduler_name())
            arg["is_running"] = F.scheduler.is_running(self.get_scheduler_name())
        return render_template(f"{P.package_name}_{self.name}_{sub}.html", arg=arg)

    def process_command(self, command, arg1, arg2, arg3, req):
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        streaming_type = P.ModelSetting.get("streaming_type")

        if command == "broad_list":
            token = self.token_refresh()
            data = PKTV_Handler.ch_list(token)
            return jsonify({"list": data, "updated_at": updated_at, "streaming_type": streaming_type})
        elif command == "play_url":
            token = self.token_refresh()
            url = arg1
            if streaming_type == "redirect":
                parsed_url = urlparse(url)
                query_params = parse_qs(parsed_url.query)

                cast_id = query_params.get("cast_id")[0]
                cast_partner_code = query_params.get("cast_partner_code")[0]
                url = PKTV_Handler.get_live_view(cast_id, cast_partner_code, token, self.web_list_model)
            ret = {"ret": "success", "data": url}
        elif command == "login_check":
            data = self.token_refresh(force=True)
            ret = {"ret": "success", "json": data}
        return jsonify(ret)

    def process_api(self, sub, req):
        try:
            if sub == "m3u":
                token = self.token_refresh()
                return PKTV_Handler.make_m3u(token)
            if sub == "playlist":
                return PKTV_Handler.make_playlist(self.web_list_model)
            elif sub == "yaml":
                token = self.token_refresh()
                return PKTV_Handler.make_yaml(token)
            elif sub == "url.m3u8":
                token = self.token_refresh()
                return PKTV_Handler.url_m3u8(req, token, self.web_list_model)
            elif sub == "play":
                return PKTV_Handler.play(req)
            elif sub == "segment":
                return PKTV_Handler.segment(req)

        except Exception as e:
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())

    def scheduler_function(self):
        try:
            PKTV_Handler.sync_yaml_data()
        except Exception as e:
            P.logger.error(f"Exception:{str(e)}")
            P.logger.error(traceback.format_exc())

    def token_refresh(self, force=False):
        flag = False
        form = "%Y-%m-%d %H:%M:%S"
        if force:
            flag = True
        if flag == False and P.ModelSetting.get("token") == "":
            flag = True
        if flag == False:
            last_time_str = P.ModelSetting.get("token_time")
            if last_time_str == "":
                flag = True
            else:
                last_time = datetime.strptime(last_time_str, form)
                if last_time + timedelta(hours=P.ModelSetting.get_int("token_refresh_hour")) < datetime.now():
                    flag = True
        if flag:
            data = PKTV_Handler.login(P.ModelSetting.get("username"), P.ModelSetting.get("password"))
            if data:
                P.ModelSetting.set("token", data)
                P.ModelSetting.set("token_time", datetime.now().strftime(form))
            return data
        return P.ModelSetting.get("token")

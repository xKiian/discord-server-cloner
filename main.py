from httpx      import Client
from base64     import b64encode
from time       import sleep
from colorama   import Fore, init
from time       import strftime
from json       import loads

init(autoreset=True)

def p(text: str) -> None:
    print(
        f"{Fore.LIGHTWHITE_EX}[{Fore.CYAN}{strftime('%H:%M:%S')}{Fore.LIGHTWHITE_EX}] {text}"
        .replace('[+]', f'[{Fore.LIGHTGREEN_EX}+{Fore.LIGHTWHITE_EX}]')
        .replace('[*]', f'[{Fore.LIGHTYELLOW_EX}*{Fore.LIGHTWHITE_EX}]')
        .replace('[>]', f'[{Fore.CYAN}>{Fore.LIGHTWHITE_EX}]')
        .replace('[-]', f'[{Fore.RED}-{Fore.LIGHTWHITE_EX}]')
    )

class Scrape:
    def __init__(self, token: str, id: str) -> None:
        self.token      = token
        self.id         = id
        self.baseurl    = f"https://discord.com/api/v9/guilds/{self.id}"
        self.session    = Client()
        self.headers    = {"Authorization": self.token}

    def do_request(self, url) -> dict:
        return self.session.get(
            url     = url,
            headers = self.headers,
        ).json()

    def get_channels(self) -> dict:
        return self.do_request(f"{self.baseurl}/channels")

    def get_info(self) -> dict:
        return self.do_request(self.baseurl)

    def get_data(self) -> dict:
        info = self.get_info()
        return {
            "info"      : info,
            "channels"  : self.get_channels(),
            "roles"     : info["roles"],
            "emojis"    : info["emojis"],
        }


class Create:
    def __init__(self, token: str, data: dict) -> None:
        self.token      = token
        self.baseurl    = "https://discord.com/api/v9"
        self.session    = Client()
        self.data       = data
        self.headers    = {"Authorization": self.token}
        self.delay      = 0.5 # i woudn't change this

    def create_server(self):
        p("[>] Creating server")
        img = f"https://cdn.discordapp.com/icons/{self.data['info']['id']}/{self.data['info']['icon']}.webp?size=96"
        img = f"data:image/png;base64,{b64encode(self.session.get(img).content).decode('utf-8')}"
        data = {
            "name"                  : self.data["info"]["name"],
            "icon"                  : img,
            "channels"              : [],
            "system_channel_id"     : None,
            "guild_template_code"   : "8ewECn5UKpDY",
        }

        res = self.session.post(
            url     = f"{self.baseurl}/guilds",
            headers = self.headers,
            json    = data,
        ).json()

        self.id         = res["id"]
        self.everyone   = res["roles"][0]["id"]
        url             = f"{self.baseurl}/guilds/{self.id}/roles/{self.everyone}"
        data            = {
            "name"          : "@everyone",
            "permissions"   : "1071698529857",
            "color"         : 0,
            "hoist"         : False,
            "mentionable"   : False,
            "icon"          : None,
            "unicode_emoji" : None,
        }
        self.session.patch(
            url     = url,
            headers = self.headers,
            json    = data,
        )

        url     = f"{self.baseurl}/guilds/{self.id}"
        data    = {
            "features"                      : ["APPLICATION_COMMAND_PERMISSIONS_V2", "COMMUNITY"],
            "verification_level"            : 1,
            "default_message_notifications" : 1,
            "explicit_content_filter"       : 2,
            "rules_channel_id"              : "1",
            "public_updates_channel_id"     : "1",
        }
        self.session.patch(
            url     = url,
            headers = self.headers,
            json    = data,
        )

        p(f"[+] Created server {self.data['info']['name']} -> {res['id']}")

    def delete_channels(self):
        channels = self.session.get(
            url     = f"{self.baseurl}/guilds/{self.id}/channels",
            headers = self.headers,
        ).json()

        for channel in channels:
            s = self.session.delete(
                url     = f"{self.baseurl}/channels/{channel['id']}",
                headers = self.headers,
            ).status_code

            p(f"[+] Deleted channel {channel['name']} -> {s}" if s == 200 else f"[-] Failed to delete channel {channel['name']} -> {s}")

    def create_channels(self):
        parentchannels = sorted([channel for channel in self.data["channels"] if channel["type"] == 4] , key=lambda x: x["position"])
        prnt = {}

        p(f"[>] Creating {len(parentchannels)} parent channels")

        for channel in parentchannels:
            data = {
                "name"                  : channel["name"],
                "type"                  : channel["type"],
                "permission_overwrites" : channel["permission_overwrites"],
            }

            res = self.session.post(
                url     = f"{self.baseurl}/guilds/{self.id}/channels",
                headers = self.headers,
                json    = data,
            )

            p(f"[+] Created channel {channel['name']} -> {res.status_code}" if res.status_code == 201 else f"[-] Failed to create channel {channel['name']} -> {res.status_code}")
            prnt[channel["id"]] = res.json()["id"]
            sleep(self.delay)

        p(f"[>] Creating {len(self.data['channels']) - len(parentchannels)} channels")

        for channel in self.data["channels"]:
            if channel["type"] == 4: continue

            data = {
                "name"                  : channel["name"],
                "type"                  : channel["type"],
                "permission_overwrites" : channel["permission_overwrites"],
            }

            if channel["parent_id"]:
                data  ["parent_id"] = prnt[channel["parent_id"]]

            res = self.session.post(
                url     = f"{self.baseurl}/guilds/{self.id}/channels",
                headers = self.headers,
                json    = data,
            )
            p(f"[+] Created channel {channel['name']} -> {res.status_code}" if res.status_code == 201 else f"[-] Failed to create channel {channel['name']} -> {res.status_code}")
            sleep(self.delay)

    def create_roles(self):
        roles = self.data["roles"]
        roles = sorted(roles, key=lambda x: x["position"], reverse=True)

        p(f"[>] Creating {len(roles)} roles")

        for role in roles:
            if role["name"] == "@everyone":
                for channel in self.data["channels"]:
                    for permission in channel["permission_overwrites"]:
                        if permission["id"] == role["id"]:
                            permission["id"] = self.everyone
                continue
            data = {
                "name"          : role["name"],
                "permissions"   : role["permissions"],
                "color"         : role["color"],
                "hoist"         : role["hoist"],
                "mentionable"   : role["mentionable"],
                "icon"          : None,
                "unicode_emoji" : None,
            }

            res = self.session.post(
                url     = f"{self.baseurl}/guilds/{self.id}/roles",
                headers = self.headers,
                json    = data,
            )

            p(f"[+] Created role {role['name']} -> {res.status_code}" if res.status_code == 200 else f"[-] Failed to create role {role['name']} -> {res.status_code})")

            for channel in self.data["channels"]:
                if channel["type"] == 4: continue

                for permission in channel["permission_overwrites"]:
                    if permission["id"] == role["id"]:
                        permission["id"] = res.json()["id"]
            sleep(self.delay)

    def create_emojis(self):
        p(f"[>] Creating {len(self.data['emojis'])} emojis" if len(self.data["emojis"]) > 0 else "[!] No emojis to create")
        for emoji in self.data["emojis"]:
            img         = f"https://cdn.discordapp.com/emojis/{emoji['id']}.png"
            img         = f"data:image/png;base64,{b64encode(self.session.get(img).content).decode('utf-8')}"
            data        = {
                "name"  : emoji["name"],
                "image" : img,
                "roles" : emoji["roles"]
            }
            s = self.session.post(
                url     = f"{self.baseurl}/guilds/{self.id}/emojis",
                headers = self.headers,
                json    = data,
            ).status_code
            p(f"[+] Created emoji {emoji['name']} -> {s}" if s == 201 else f"[-] Failed to create emoji {emoji['name']} -> {s}")
            sleep(self.delay)

    def all(self):
        tasks = [
            self.create_server,
            self.delete_channels,
            self.create_channels,
            self.create_roles,
            self.create_emojis,
        ] # phish will hate
        for task in tasks:
            try: task()
            except Exception as e:
                p(f"[*] {e}")
                pass


if __name__ == "__main__":
    config  = loads(open("config.json", "r").read())
    token   = config["token"]
    id      = input("[?] Server ID: ")
    data    = Scrape(token, id).get_data()
    Create(token, data).all()
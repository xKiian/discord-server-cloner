from httpx  import Client
from base64 import b64encode
from time   import sleep

class Scrape:
    def __init__(self, token: str, id: str) -> None:
        self.token = token
        self.id = id
        self.baseurl = "https://discord.com/api/v9"
        self.session = Client()

    def get_channels(self):
        return self.session.get(
            f"{self.baseurl}/guilds/{self.id}/channels",
            headers={"Authorization": self.token},
        ).json()

    
    def get_info(self):
        return self.session.get(
            f"{self.baseurl}/guilds/{self.id}",
            headers={"Authorization": self.token},
        ).json()
    
    def get_data(self):
        info = self.get_info()
        return {
            "info"          : info,
            "channels"      : self.get_channels(),
            "roles"         : info["roles"],
            "emojis"        : info["emojis"],
        }


class Create:
    def __init__(self, token: str, data: dict) -> None:
        self.token = token
        self.baseurl = "https://discord.com/api/v9"
        self.session = Client()
        self.data = data

    def create_server(self):
        img = f"https://cdn.discordapp.com/icons/{self.data['info']['id']}/{self.data['info']['icon']}.webp?size=96"
        img = f"data:image/png;base64,{b64encode(self.session.get(img).content).decode('utf-8')}"
        data = {
            "name": self.data["info"]["name"],
            "icon": img,
            "channels": [],
            "system_channel_id": None,
            "guild_template_code": "8ewECn5UKpDY"
        }

        res = self.session.post(
            f"{self.baseurl}/guilds",
            headers={"Authorization": self.token},
            json=data,
        ).json()
        self.id         = res["id"]
        self.everyone   = res["roles"][0]["id"]
        url             = f"{self.baseurl}/guilds/{self.id}/roles/{self.everyone}"
        data = {
            "name"          : "@everyone",
            "permissions"   : "1071698529857",
            "color"         : 0,
            "hoist"         : False,
            "mentionable"   : False,
            "icon"          : None,
            "unicode_emoji" : None
        }
        self.session.patch(
            url,
            headers={"Authorization": self.token},
            json=data,
        )

        url = f"{self.baseurl}/guilds/{self.id}"
        data = {
            "features": [
              "APPLICATION_COMMAND_PERMISSIONS_V2",
              "COMMUNITY"
            ],
            "verification_level": 1,
            "default_message_notifications": 1,
            "explicit_content_filter": 2,
            "rules_channel_id": "1",
            "public_updates_channel_id": "1"
        }
        self.session.patch(
            url,
            headers={"Authorization": self.token},
            json=data,
        )

        print("[+] Created server")

    def delete_channels(self):
        channels = self.session.get(
            f"{self.baseurl}/guilds/{self.id}/channels",
            headers={"Authorization": self.token},
        ).json()
        for channel in channels:
            self.session.delete(
                f"{self.baseurl}/channels/{channel['id']}",
                headers={"Authorization": self.token},
            )
            print(f"[+] Deleted channel {channel['name']}")

    def create_channels(self):
        parentchannels = [channel for channel in self.data["channels"] if channel["type"] == 4]
        parentchannels = sorted(parentchannels, key=lambda x: x["position"])
        prnt = {}
        print(f"[+] Creating {len(parentchannels)} parent channels")
        for channel in parentchannels:
            data = {
                "name": channel["name"],
                "type": channel["type"],
                "permission_overwrites": channel["permission_overwrites"],
            }
            res = self.session.post(
                f"{self.baseurl}/guilds/{self.id}/channels",
                headers={"Authorization": self.token},
                json=data,
            ).json()
            print(f"[+] Created channel {channel['name']}")
            prnt[channel["id"]] = res["id"]
            sleep(1)

        print(f"[+] Creating {len(self.data['channels']) - len(parentchannels)} channels")
        for channel in self.data["channels"]:
            if channel["type"] == 4:
                continue
            data = {
                "name": channel["name"],
                "type": channel["type"],
                "permission_overwrites": channel["permission_overwrites"],
            }
            if channel["parent_id"]:
                data["parent_id"] = prnt[channel["parent_id"]]
            res = self.session.post(
                f"{self.baseurl}/guilds/{self.id}/channels",
                headers={"Authorization": self.token},
                json=data,
            ).json()
            print(f"[+] Created channel {channel['name']}")
            sleep(1)

    def create_roles(self):
        roles = self.data["roles"]
        roles = sorted(roles, key=lambda x: x["position"], reverse=True)
        print(f"[+] Creating {len(roles)} roles")
        for role in roles:
            if role["name"] == "@everyone":
                for channel in self.data["channels"]:
                    for permission in channel["permission_overwrites"]:
                        if permission["id"] == role["id"]:
                            permission["id"] = self.everyone
            data = {
                "name": role["name"],
                "permissions": role["permissions"],
                "color": role["color"],
                "hoist": role["hoist"],
                "mentionable": role["mentionable"],
                "icon": None,
                "unicode_emoji": None,
            }
            res = self.session.post(
                f"{self.baseurl}/guilds/{self.id}/roles",
                headers={"Authorization": self.token},
                json=data,
            )
            print(f"[+] Created role {role['name']}")
            for channel in self.data["channels"]:
                if channel["type"] == 4:
                    continue
                for permission in channel["permission_overwrites"]:
                    if permission["id"] == role["id"]:
                        permission["id"] = res.json()["id"]
            sleep(1)
        
    def create_emojis(self):
        for emoji in self.data["emojis"]:
            img = f"https://cdn.discordapp.com/emojis/{emoji['id']}.png"
            img = f"data:image/png;base64,{b64encode(self.session.get(img).content).decode('utf-8')}"
            data = {
                "name": emoji["name"],
                "image": img,
                "roles": emoji["roles"],
            }
            self.session.post(
                f"{self.baseurl}/guilds/{self.id}/emojis",
                headers={"Authorization": self.token},
                json=data,
            )
            print(f"[+] Created emoji {emoji['name']}")
            sleep(1)
    

    def all(self):
        self.create_server()
        self.delete_channels()
        self.create_roles()
        self.create_channels()
        self.create_emojis()
        return  "[+] Done! (with rizz)"


if __name__ == "__main__":
    token   = "MTA4MTUzMTMzOTcyNTA5MDgzNg.GbUZBW.Wka_Shz7dQEOsSpiKZ96mvgozlj8RqiLI7-7uQ"
    id      = "1052478335923539998"
    data    = Scrape(token, id).get_data()
    print(Create(token, data).all())
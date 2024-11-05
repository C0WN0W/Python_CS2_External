import Utils
import Configs as cfg

pm = Utils.get_pyMeow()
rq = Utils.get_requests()


class Offsets:
    m_pBoneArray = 496


class Colors:
    green = pm.get_color("#00FF00")
    orange = pm.fade_color(pm.get_color("#FFA500"), 0.3)
    black = pm.get_color("black")
    cyan = pm.fade_color(pm.get_color("#00F6F6"), 0.3)
    white = pm.get_color("white")
    grey = pm.fade_color(pm.get_color("#242625"), 0.7)


class Entity:
    def __init__(self, ptr, pawn_ptr, proc):
        self.ptr = ptr
        self.pawn_ptr = pawn_ptr
        self.proc = proc
        self.pos2d = None
        self.head_pos2d = None

    @property
    def name(self):
        return pm.r_string(self.proc, self.ptr + Offsets.m_iszPlayerName)

    @property
    def health(self):
        return pm.r_int(self.proc, self.pawn_ptr + Offsets.m_iHealth)

    @property
    def team(self):
        return pm.r_int(self.proc, self.pawn_ptr + Offsets.m_iTeamNum)

    @property
    def pos(self):
        return pm.r_vec3(self.proc, self.pawn_ptr + Offsets.m_vOldOrigin)
    
    @property
    def dormant(self):
        return pm.r_bool(self.proc, self.pawn_ptr + Offsets.m_bDormant)

    def bone_pos(self, bone):
        game_scene = pm.r_int64(self.proc, self.pawn_ptr + Offsets.m_pGameSceneNode)
        bone_array_ptr = pm.r_int64(self.proc, game_scene + Offsets.m_pBoneArray)
        return pm.r_vec3(self.proc, bone_array_ptr + bone * 32)
    
    def wts(self, view_matrix):
        try:
            self.pos2d = pm.world_to_screen(view_matrix, self.pos, 1)
            self.head_pos2d = pm.world_to_screen(view_matrix, self.bone_pos(6), 1)
        except:
            return False
        return True

class Render:
    def draw_health(max, current, PosX, PosY, width, height):
        if cfg.ESP.show_health:
            Proportion = current / max
            Height = height * Proportion
            offsetY = height * (max - current) / max

            pm.draw_rectangle(PosX + 1, PosY + 1 + offsetY, width / 2, Height, Colors.green)
            pm.draw_rectangle_lines(PosX, PosY, width, height, Colors.black)

    def draw_box(PosX, PosY, width, height, color, filled_color):
        if cfg.ESP.show_filled_box:
            pm.draw_rectangle(PosX, PosY, width, height, filled_color)
        if cfg.ESP.show_box:
            pm.draw_rectangle_lines(PosX, PosY, width, height, color, 1.2)

class Esp:
    def __init__(self):
        self.proc = pm.open_process("cs2.exe")
        self.mod = pm.get_module(self.proc, "client.dll")["base"]

        offsets_name = ["dwViewMatrix", "dwEntityList", "dwLocalPlayerController", "dwLocalPlayerPawn"]
        offsets = rq.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/offsets.json").json()
        [setattr(Offsets, k, offsets["client.dll"][k]) for k in offsets_name]
        client_dll_name = {
            "m_iIDEntIndex": "C_CSPlayerPawnBase",
            "m_hPlayerPawn": "CCSPlayerController",
            "m_fFlags": "C_BaseEntity",
            "m_iszPlayerName": "CBasePlayerController",
            "m_iHealth": "C_BaseEntity",
            "m_iTeamNum": "C_BaseEntity",
            "m_vOldOrigin": "C_BasePlayerPawn",
            "m_pGameSceneNode": "C_BaseEntity",
            "m_bDormant": "CGameSceneNode",
        }
        clientDll = rq.get("https://raw.githubusercontent.com/a2x/cs2-dumper/main/output/client_dll.json").json()
        [setattr(Offsets, k, clientDll["client.dll"]["classes"][client_dll_name[k]]["fields"][k]) for k in client_dll_name]

    def it_entities(self):
        ent_list = pm.r_int64(self.proc, self.mod + Offsets.dwEntityList)
        local = pm.r_int64(self.proc, self.mod + Offsets.dwLocalPlayerController)
        for i in range(1, 65):
            try:
                entry_ptr = pm.r_int64(self.proc, ent_list + (8 * (i & 0x7FFF) >> 9) + 16)
                controller_ptr = pm.r_int64(self.proc, entry_ptr + 120 * (i & 0x1FF))
                if controller_ptr == local:
                    continue
                controller_pawn_ptr = pm.r_int64(self.proc, controller_ptr + Offsets.m_hPlayerPawn)
                list_entry_ptr = pm.r_int64(self.proc, ent_list + 0x8 * ((controller_pawn_ptr & 0x7FFF) >> 9) + 16)
                pawn_ptr = pm.r_int64(self.proc, list_entry_ptr + 120 * (controller_pawn_ptr & 0x1FF))
            except:
                continue

            yield Entity(controller_ptr, pawn_ptr, self.proc)

    def run(self):
        pm.overlay_init("Counter-Strike 2", fps=144)
        while pm.overlay_loop():
            view_matrix = pm.r_floats(self.proc, self.mod + Offsets.dwViewMatrix, 16)

            pm.begin_drawing()
            pm.draw_fps(0, 0)
            for ent in self.it_entities():
                if ent.wts(view_matrix) and ent.health > 0 and not ent.dormant:
                    color = Colors.cyan if ent.team != 2 else Colors.orange
                    head = ent.pos2d["y"] - ent.head_pos2d["y"]
                    width = head / 2
                    center = width / 2
                    health = ent.head_pos2d["y"] - center / 2 + ent.health + 1

                    if cfg.ESP.show_line:
                        pm.draw_line(pm.get_screen_width() / 2, 0, ent.head_pos2d["x"], ent.head_pos2d["y"] - center / 2, Colors.white, 0.5)
                    
                    Render.draw_box(ent.head_pos2d["x"] - center, ent.head_pos2d["y"] - center / 2, width, head + center / 2, Colors.white, color)
                    Render.draw_health(100, ent.health, 
                                        ent.head_pos2d["x"] + center + 2,
                                        ent.head_pos2d["y"] - center / 2, 
                                        4, 
                                        head + center / 2)
            
            pm.end_drawing()
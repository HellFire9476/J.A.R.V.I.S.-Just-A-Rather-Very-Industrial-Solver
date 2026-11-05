import pandas as pd
import customtkinter as ctk
import math
import os
import sys
import json
import ctypes
import struct
import shutil
import re
import tkinter as tk
import threading
import queue
import subprocess
import webbrowser
from tkinter import filedialog, colorchooser
from updater import download_release_asset, fetch_latest_release, launch_windows_updater, parse_version
# ==============================================================================
# 1. IDENTITÉ PRO, ICÔNE AUTO-GÉNÉRÉE & ARBORESCENCE PAR DOSSIERS D'USINES
# ==============================================================================
NOM_LOGICIEL = "J.A.R.V.I.S. — Just A Rather Very Industrial Solver"
VERSION_APPLICATION = "1.0.1"
DEPOT_GITHUB = "HellFire9476/J.A.R.V.I.S.-Just-A-Rather-Very-Industrial-Solver"
NOM_DOSSIER_RACINE = "FRIDAY_OS"
if getattr(sys, 'frozen', False):
    DOSSIER_APP = os.path.dirname(sys.executable)
    DOSSIER_INTERNE = getattr(sys, '_MEIPASS', DOSSIER_APP)
else:
    DOSSIER_APP = os.path.dirname(os.path.abspath(__file__))
    DOSSIER_INTERNE = DOSSIER_APP
csv_externe = os.path.join(DOSSIER_APP, 'Planificateur Satisfactory - Recettes.csv')
csv_interne = os.path.join(DOSSIER_INTERNE, 'Planificateur Satisfactory - Recettes.csv')
nom_fichier = csv_externe if os.path.exists(csv_externe) else csv_interne
def generer_icone_ico_si_absente(chemin_ico):
    """Génère automatiquement un fichier icone.ico 32x32 valide s'il est absent."""
    if os.path.exists(chemin_ico):
        return
    try:
        w, h = 32, 32
        pixels = bytearray()
        for y in range(h):
            for x in range(w):
                dx, dy = x - 15.5, y - 15.5
                dist = (dx*dx + dy*dy) ** 0.5
                if dist > 15.0:
                    pixels.extend((0, 0, 0, 0))
                elif dist > 12.2:
                    pixels.extend((11, 158, 245, 255))  # Couronne Ambre/Or
                else:
                    if (abs(dx) < 3.2 and abs(dy) < 9.0) or (abs(dy) < 3.2 and abs(dx) < 9.0):
                        pixels.extend((255, 255, 255, 255))
                    else:
                        pixels.extend((216, 78, 29, 255))  # Bleu Royal Nexus
        and_mask = bytearray(((w + 31) // 32) * 4 * h)
        bih = struct.pack('<IIIHHIIIIII', 40, w, h * 2, 1, 32, 0, len(pixels) + len(and_mask), 0, 0, 0, 0)
        img_data = bih + pixels + and_mask
        ico_header = struct.pack('<HHH', 0, 1, 1)
        ico_dir = struct.pack('<BBBBHHII', w, h, 0, 0, 1, 32, len(img_data), 22)
        with open(chemin_ico, 'wb') as f:
            f.write(ico_header + ico_dir + img_data)
    except Exception:
        pass
chemin_icone_local = os.path.join(DOSSIER_APP, 'icone.ico')
generer_icone_ico_si_absente(chemin_icone_local)
chemin_icone_interne = os.path.join(DOSSIER_INTERNE, 'icone.ico')
chemin_icone = chemin_icone_interne if os.path.exists(chemin_icone_interne) else chemin_icone_local
def obtenir_dossier_documents():
    if os.name == 'nt':
        try:
            buf = ctypes.create_unicode_buffer(260)
            ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf)
            if buf.value:
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")
DOSSIER_RACINE_DOCS = os.path.join(obtenir_dossier_documents(), NOM_DOSSIER_RACINE)
DOSSIER_CONFIG_GLOBALE = os.path.join(DOSSIER_RACINE_DOCS, "Config_Globale")
DOSSIER_TOUTES_USINES = os.path.join(DOSSIER_RACINE_DOCS, "Usines")
os.makedirs(DOSSIER_CONFIG_GLOBALE, exist_ok=True)
os.makedirs(DOSSIER_TOUTES_USINES, exist_ok=True)
fichier_mods = os.path.join(DOSSIER_CONFIG_GLOBALE, 'mods_config.json')
fichier_settings = os.path.join(DOSSIER_CONFIG_GLOBALE, 'user_settings.json')
def nettoyer_nom_dossier(nom):
    propre = re.sub(r'[<>:"/\\|?*]', '_', str(nom).strip())
    return propre if propre else "Usine_Principale"
def obtenir_dossier_usine(nom_usine):
    d = os.path.join(DOSSIER_TOUTES_USINES, nettoyer_nom_dossier(nom_usine))
    os.makedirs(d, exist_ok=True)
    return d
# ==============================================================================
# 2. THÈMES (SOMBRE, ABYSSAL, CLAIR) & PERSONNALISATION
# ==============================================================================
THEMES_BASE = {
    "Sombre": {
        "ctk_mode": "Dark",
        "bg_main": "#0F172A", "bg_panel": "#1E293B", "bg_card": "#26334D", "bg_card_alt": "#0B1120",
        "border": "#3B4F6B", "text_main": "#F8FAFC", "text_muted": "#94A3B8",
        "default_tab_sel": "#1D4ED8", "default_seg_sel": "#0369A1"
    },
    "Abyssal": {
        "ctk_mode": "Dark",
        "bg_main": "#02040A", "bg_panel": "#070B14", "bg_card": "#0D1322", "bg_card_alt": "#04070E",
        "border": "#1E293B", "text_main": "#E2E8F0", "text_muted": "#64748B",
        "default_tab_sel": "#312E81", "default_seg_sel": "#1E3A8A"
    },
    "Clair": {
        "ctk_mode": "Light",
        "bg_main": "#E2E8F0", "bg_panel": "#F1F5F9", "bg_card": "#FFFFFF", "bg_card_alt": "#CBD5E1",
        "border": "#94A3B8", "text_main": "#0F172A", "text_muted": "#334155",
        "default_tab_sel": "#1E3A8A", "default_seg_sel": "#065F46"
    }
}
COULEURS_PRESETS = {
    "Bleu Royal (#1D4ED8)": "#1D4ED8",
    "Indigo Spatial (#312E81)": "#312E81",
    "Bleu Océan (#0369A1)": "#0369A1",
    "Émeraude Foncé (#065F46)": "#065F46",
    "Pourpre Impérial (#5B21B6)": "#5B21B6",
    "Carmin Tactique (#991B1B)": "#991B1B",
    "Cuivre Sombre (#9A3412)": "#9A3412",
    "Ardoise Pro (#334155)": "#334155"
}
USER_SETTINGS = {
    "theme_nom": "Sombre",
    "tab_selected_color": "#1D4ED8",
    "seg_selected_color": "#0369A1",
    "derniere_usine_active": "Usine Principale"
}
if os.path.exists(fichier_settings):
    try:
        with open(fichier_settings, "r", encoding="utf-8") as f:
            USER_SETTINGS.update(json.load(f))
    except Exception:
        pass
def sauvegarder_settings():
    try:
        with open(fichier_settings, "w", encoding="utf-8") as f:
            json.dump(USER_SETTINGS, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
def get_theme():
    t_nom = USER_SETTINGS.get("theme_nom", "Sombre")
    if t_nom not in THEMES_BASE:
        t_nom = "Sombre"
    base = dict(THEMES_BASE[t_nom])
    base["tab_sel"] = USER_SETTINGS.get("tab_selected_color", base["default_tab_sel"])
    base["seg_sel"] = USER_SETTINGS.get("seg_selected_color", base["default_seg_sel"])
    base["status_ok"] = "#10B981" if base["ctk_mode"] == "Dark" else "#059669"
    base["status_warn"] = "#F59E0B" if base["ctk_mode"] == "Dark" else "#B45309"
    base["status_err"] = "#EF4444" if base["ctk_mode"] == "Dark" else "#DC2626"
    base["accent_purple"] = "#6D28D9"
    return base
THEME = get_theme()
def recolorer_scrollable(sf, couleur_fond):
    try:
        sf.configure(fg_color=couleur_fond)
        if hasattr(sf, "_parent_canvas"):
            sf._parent_canvas.configure(bg=couleur_fond)
        if hasattr(sf, "_parent_frame"):
            sf._parent_frame.configure(fg_color=couleur_fond)
    except Exception:
        pass
# ==============================================================================
# 3. POPUPS ARRONDIS AVEC LIBÉRATION STRICTE DU FOCUS CLAVIER WINDOWS
# ==============================================================================
class PopupCustom:
    def __init__(self, master, titre, message, type_popup="info", valeur_initiale=""):
        self.result = None
        self.master_ref = master
        self.top = ctk.CTkToplevel(master)
        self.top.title(titre)
        self.top.overrideredirect(True)
        self.top.attributes("-topmost", True)
        self.top.transient(master)
        trans_key = "#000001"
        try:
            if os.name == "nt":
                self.top.configure(fg_color=trans_key)
                self.top.wm_attributes("-transparentcolor", trans_key)
            else:
                self.top.configure(fg_color=THEME["bg_main"])
        except Exception:
            self.top.configure(fg_color=THEME["bg_main"])
        largeur = 520
        hauteur = 270 if type_popup == "input" else 230
        self.top.update_idletasks()
        x = master.winfo_rootx() + (master.winfo_width() - largeur) // 2
        y = master.winfo_rooty() + (master.winfo_height() - hauteur) // 2
        self.top.geometry(f"{largeur}x{hauteur}+{max(x, 40)}+{max(y, 40)}")
        c_map = {
            "error": (THEME["status_err"], "⚠️"),
            "warning": (THEME["status_warn"], "⚡"),
            "success": (THEME["status_ok"], "✅"),
            "yesno": (THEME["status_err"], "🗑️"),
            "update": (THEME["tab_sel"], "⬆️"),
            "input": (THEME["tab_sel"], "✏️")
        }
        c_accent, icone = c_map.get(type_popup, (THEME["tab_sel"], "ℹ️"))
        self.card = ctk.CTkFrame(self.top, fg_color=THEME["bg_panel"], border_color=c_accent, border_width=2, corner_radius=18)
        self.card.pack(fill="both", expand=True, padx=2, pady=2)
        self.header_bar = ctk.CTkFrame(self.card, fg_color=THEME["bg_card_alt"], corner_radius=14, height=42)
        self.header_bar.pack(fill="x", padx=8, pady=(8, 10))
        self.lbl_titre = ctk.CTkLabel(
            self.header_bar, text=f"{icone}  {titre.upper()}",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            text_color=c_accent if type_popup in ["error", "warning", "success"] else THEME["text_main"]
        )
        self.lbl_titre.pack(side="left", padx=14, pady=8)
        ctk.CTkButton(
            self.header_bar, text="✕", width=28, height=26, corner_radius=8,
            fg_color=THEME["bg_card"], hover_color=THEME["status_err"], text_color=THEME["text_main"],
            command=self.on_no
        ).pack(side="right", padx=8, pady=6)
        self._drag_x, self._drag_y = 0, 0
        for w_d in (self.header_bar, self.lbl_titre):
            w_d.bind("<ButtonPress-1>", self._start_move)
            w_d.bind("<B1-Motion>", self._on_move)
        ctk.CTkLabel(self.card, text=message, font=ctk.CTkFont(size=13), text_color=THEME["text_main"], wraplength=460, justify="center").pack(padx=20, pady=(4, 12), expand=True)
        if type_popup == "input":
            self.entry = ctk.CTkEntry(
                self.card, width=380, height=38, corner_radius=10,
                fg_color=THEME["bg_card"], text_color=THEME["text_main"],
                border_color=THEME["tab_sel"], border_width=2,
                font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), justify="center"
            )
            self.entry.pack(pady=(0, 14))
            if valeur_initiale:
                self.entry.insert(0, valeur_initiale)
            self.top.after(40, lambda: self.entry.focus_force())
            self.entry.bind("<Return>", lambda e: self.on_input_ok())
        btn_frame = ctk.CTkFrame(self.card, fg_color=THEME["bg_panel"])
        btn_frame.pack(pady=(0, 16))
        if type_popup in ["info", "error", "warning", "success"]:
            ctk.CTkButton(btn_frame, text="✓  VALIDER", width=150, height=36, corner_radius=10, fg_color=THEME["tab_sel"] if type_popup == "info" else c_accent, hover_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=self.on_ok).pack()
            self.top.bind("<Return>", lambda e: self.on_ok())
        elif type_popup in ["yesno", "update"]:
            texte_confirmer = "↻  REDÉMARRER" if type_popup == "update" else "✓  CONFIRMER"
            texte_annuler = "PLUS TARD" if type_popup == "update" else "✕  ANNULER"
            couleur_confirmer = THEME["tab_sel"] if type_popup == "update" else THEME["status_err"]
            ctk.CTkButton(btn_frame, text=texte_confirmer, width=145, height=36, corner_radius=10, fg_color=couleur_confirmer, hover_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=self.on_yes).pack(side="left", padx=8)
            ctk.CTkButton(btn_frame, text=texte_annuler, width=145, height=36, corner_radius=10, fg_color=THEME["bg_card"], hover_color=THEME["border"], text_color=THEME["text_main"], font=ctk.CTkFont(size=12, weight="bold"), command=self.on_no).pack(side="left", padx=8)
        elif type_popup == "input":
            ctk.CTkButton(btn_frame, text="✓  VALIDER", width=155, height=36, corner_radius=10, fg_color=THEME["tab_sel"], hover_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=self.on_input_ok).pack(side="left", padx=8)
            ctk.CTkButton(btn_frame, text="✕  ANNULER", width=140, height=36, corner_radius=10, fg_color=THEME["bg_card"], hover_color=THEME["border"], text_color=THEME["text_main"], font=ctk.CTkFont(size=12, weight="bold"), command=self.on_no).pack(side="left", padx=8)
        self.top.bind("<Escape>", lambda e: self.on_no())
        self.top.grab_set()
    def _start_move(self, event):
        self._drag_x, self._drag_y = event.x, event.y
    def _on_move(self, event):
        self.top.geometry(f"+{self.top.winfo_x() + (event.x - self._drag_x)}+{self.top.winfo_y() + (event.y - self._drag_y)}")
    def _fermer_proprement(self):
        """Libère impérativement le grab et rend le focus clavier à la fenêtre principale."""
        try:
            self.top.grab_release()
        except Exception:
            pass
        try:
            self.top.destroy()
            self.master_ref.after(30, lambda: self.master_ref.focus_force())
        except Exception:
            pass
    def on_ok(self): self.result = True; self._fermer_proprement()
    def on_yes(self): self.result = True; self._fermer_proprement()
    def on_no(self): self.result = False if not hasattr(self, "entry") else None; self._fermer_proprement()
    def on_input_ok(self): self.result = self.entry.get(); self._fermer_proprement()
    def get(self):
        self.top.wait_window()
        return self.result
def popup_info(titre, message): return PopupCustom(app, titre, message, "info").get()
def popup_success(titre, message): return PopupCustom(app, titre, message, "success").get()
def popup_warning(titre, message): return PopupCustom(app, titre, message, "warning").get()
def popup_error(titre, message): return PopupCustom(app, titre, message, "error").get()
def popup_askyesno(titre, message): return PopupCustom(app, titre, message, "yesno").get()
def popup_askupdate(titre, message): return PopupCustom(app, titre, message, "update").get()
def popup_askstring(titre, message, initialvalue=""): return PopupCustom(app, titre, message, "input", initialvalue).get()

_queue_maj = queue.Queue()
_verification_maj_active = False

def _surveiller_resultat_maj():
    global _verification_maj_active
    try:
        action, resultat, manuelle = _queue_maj.get_nowait()
    except queue.Empty:
        if _verification_maj_active:
            app.after(100, _surveiller_resultat_maj)
        return

    _verification_maj_active = False
    if action == "erreur":
        if manuelle:
            popup_error("Vérification des mises à jour", str(resultat))
        return
    if action == "erreur_telechargement":
        popup_error("Téléchargement de la mise à jour", str(resultat))
        return

    if action == "verification":
        version_locale = parse_version(VERSION_APPLICATION)
        if resultat.version <= version_locale:
            if manuelle:
                popup_info("Mises à jour", f"J.A.R.V.I.S. est à jour ({VERSION_APPLICATION}).")
            return
        _demarrer_telechargement_maj(resultat)
        return

    if action == "telechargement":
        if not popup_askupdate(
            "Mise à jour prête",
            f"La version {resultat[0].tag} a été téléchargée et vérifiée.\n\n"
            "Redémarrer maintenant pour l'installer ? Vos usines et réglages enregistrés "
            "seront conservés. Si tu choisis « Plus tard », l'application gardera la version actuelle.",
        ):
            try:
                os.remove(resultat[1])
            except OSError as error:
                popup_error("Nettoyage de la mise à jour", f"Impossible de supprimer le fichier temporaire :\n{error}")
            return
        try:
            launch_windows_updater(resultat[1], sys.executable, os.getpid())
        except (OSError, subprocess.SubprocessError) as error:
            try:
                os.remove(resultat[1])
            except OSError:
                pass
            popup_error("Installation de la mise à jour", f"Impossible de préparer la mise à jour :\n{error}")
            return
        app.destroy()

def _demarrer_telechargement_maj(release):
    global _verification_maj_active
    _verification_maj_active = True

    def telecharger():
        try:
            path = download_release_asset(release)
            _queue_maj.put(("telechargement", (release, path), False))
        except Exception as error:
            _queue_maj.put(("erreur_telechargement", error, False))

    threading.Thread(target=telecharger, name="JARVIS-update-download", daemon=True).start()
    app.after(100, _surveiller_resultat_maj)

def verifier_mises_a_jour(manuelle=True):
    global _verification_maj_active
    if not getattr(sys, "frozen", False):
        if manuelle:
            webbrowser.open(
                f"https://github.com/{DEPOT_GITHUB}/releases/latest",
                new=2,
            )
        return
    if _verification_maj_active:
        return
    _verification_maj_active = True

    def verifier():
        try:
            release = fetch_latest_release(DEPOT_GITHUB)
            _queue_maj.put(("verification", release, manuelle))
        except Exception as error:
            _queue_maj.put(("erreur", error, manuelle))

    threading.Thread(target=verifier, name="JARVIS-update-check", daemon=True).start()
    app.after(100, _surveiller_resultat_maj)

# ==============================================================================
# 4. MOTEUR DE MODS MULTI-CATÉGORIES (PRODUCTION, EXTRACTION, ÉNERGIE, REFINED POWER)
# ==============================================================================
CATEGORIES_MACHINES = [
    "Production",
    "Extraction",
    "Énergie Directe",
    "Refined Power : Chaudière (Vapeur)",
    "Refined Power : Turbine (RPM)",
    "Refined Power : Alternateur (RPM ➔ MW)"
]
MACHINES_VANILLA = {
    "Constructeur": {"categorie": "Production", "mw": 4.0, "vitesse": 1.0, "somers_max": 1, "valeur_spec": 0.0},
    "Assembleuse": {"categorie": "Production", "mw": 15.0, "vitesse": 1.0, "somers_max": 2, "valeur_spec": 0.0},
    "Façonneuse": {"categorie": "Production", "mw": 55.0, "vitesse": 1.0, "somers_max": 4, "valeur_spec": 0.0},
    "Fonderie": {"categorie": "Production", "mw": 16.0, "vitesse": 1.0, "somers_max": 1, "valeur_spec": 0.0},
    "Fonderie avancée": {"categorie": "Production", "mw": 40.0, "vitesse": 1.0, "somers_max": 2, "valeur_spec": 0.0},
    "Raffinerie": {"categorie": "Production", "mw": 30.0, "vitesse": 1.0, "somers_max": 1, "valeur_spec": 0.0},
    "Conditionneur": {"categorie": "Production", "mw": 10.0, "vitesse": 1.0, "somers_max": 1, "valeur_spec": 0.0},
    "Mélangeur": {"categorie": "Production", "mw": 75.0, "vitesse": 1.0, "somers_max": 4, "valeur_spec": 0.0},
    "Collisionneur de hadrons": {"categorie": "Production", "mw": 250.0, "vitesse": 1.0, "somers_max": 4, "valeur_spec": 0.0},
    "Encodeur quantique": {"categorie": "Production", "mw": 1000.0, "vitesse": 1.0, "somers_max": 4, "valeur_spec": 0.0},
    "Convertisseur": {"categorie": "Production", "mw": 400.0, "vitesse": 1.0, "somers_max": 2, "valeur_spec": 0.0},
    "Pompe à eau": {"categorie": "Extraction", "mw": 20.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 120.0},
    "Extracteur de pétrole": {"categorie": "Extraction", "mw": 40.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 120.0},
    # Appareils préconfigurés pour le mod Refined Power :
    "RP Chaudière Mk.1 (Firebox)": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 5.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 60.0},
    "RP Chaudière Mk.2 (Haute Pression)": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 12.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 180.0},
    "RP Réacteur Vapeur Nucléaire": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 45.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 600.0},
    "RP Turbine à Vapeur Mk.1": {"categorie": "Refined Power : Turbine (RPM)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 1500.0},
    "RP Turbine Haute Pression Mk.2": {"categorie": "Refined Power : Turbine (RPM)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 3000.0},
    "RP Alternateur Mk.1 (100 RPM = 10 MW)": {"categorie": "Refined Power : Alternateur (RPM ➔ MW)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 0.10},
    "RP Alternateur HV Mk.2 (100 RPM = 25 MW)": {"categorie": "Refined Power : Alternateur (RPM ➔ MW)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 0.25}
}
LOIS_VANILLA = {
    "max_cadence_pct": 250,
    "gain_par_eclat_pct": 50.0,
    "exposant_surcadencage": 1.6,
    "bonus_prod_somersloop_pct": 100.0,
    "exposant_elec_somersloop": 2.0
}
MODS_CONFIG = {
    "max_cadence_pct": LOIS_VANILLA["max_cadence_pct"],
    "gain_par_eclat_pct": LOIS_VANILLA["gain_par_eclat_pct"],
    "exposant_surcadencage": LOIS_VANILLA["exposant_surcadencage"],
    "bonus_prod_somersloop_pct": LOIS_VANILLA["bonus_prod_somersloop_pct"],
    "exposant_elec_somersloop": LOIS_VANILLA["exposant_elec_somersloop"],
    "machines_custom": {k: dict(v) for k, v in MACHINES_VANILLA.items()},
    "recettes_custom": [],
    "couts_construction": {}
}
if os.path.exists(fichier_mods):
    try:
        with open(fichier_mods, "r", encoding="utf-8") as f:
            loaded_mods = json.load(f)
            for k in ["max_cadence_pct", "gain_par_eclat_pct", "exposant_surcadencage", "bonus_prod_somersloop_pct", "exposant_elec_somersloop", "recettes_custom", "couts_construction"]:
                if k in loaded_mods:
                    MODS_CONFIG[k] = loaded_mods[k]
            if "machines_custom" in loaded_mods:
                for m_nom, m_val in loaded_mods["machines_custom"].items():
                    if "categorie" not in m_val:
                        m_val["categorie"] = MACHINES_VANILLA.get(m_nom, {}).get("categorie", "Production")
                    if "valeur_spec" not in m_val:
                        m_val["valeur_spec"] = MACHINES_VANILLA.get(m_nom, {}).get("valeur_spec", 0.0)
                    MODS_CONFIG["machines_custom"][m_nom] = m_val
    except Exception:
        pass
if not isinstance(MODS_CONFIG.get("couts_construction"), dict):
    MODS_CONFIG["couts_construction"] = {}

# Données officielles complètes Refined Power & Stacks
STACKS_DEFAUT = {
    "Minerai de fer": 100, "Minerai de cuivre": 100, "Calcaire": 100, "Charbon": 100,
    "Minerai de catérium": 100, "Quartz brut": 100, "Soufre": 100, "Bauxite": 100,
    "Uranium": 100, "Minerai d'uranium": 100, "SAM": 100, "Béton": 500,
    "Fil électrique": 500, "Fil actif": 500, "Vis": 500, "Câble": 200,
    "Plaque de fer": 200, "Tige de fer": 200, "Tôle de cuivre": 200, "Tuyau en acier": 200,
    "Poutre en acier": 200, "Plaque en aluminium": 200, "Boîtier en aluminium": 200,
    "Plastique": 200, "Caoutchouc": 200, "Silice": 200, "Cristal de quartz": 200,
    "Plaque de fer renforcée": 100, "Rotor": 100, "Stator": 100, "Poutre industrielle en béton": 100,
    "Cadre modulaire": 50, "Cadre modulaire lourd": 50, "Moteur": 50, "Ordinateur": 50,
    "Superordinateur": 50, "Barre de combustible à l'uranium": 50, "Eau": 1000,
    "Pétrole brut": 1000, "Carburant": 1000, "Turbocarburant": 1000, "Azote gazeux": 1000
}
MODS_CONFIG.setdefault("stacks_custom", dict(STACKS_DEFAUT))
for k_st, v_st in STACKS_DEFAUT.items():
    MODS_CONFIG["stacks_custom"].setdefault(k_st, v_st)

def get_stack_objet(nom_obj):
    return int(MODS_CONFIG.get("stacks_custom", {}).get(nom_obj, 100))

MACHINES_RP_EXACTES = {
    "RP Wind Turbine Mk1 (30 MW)": {"categorie": "Énergie Directe", "mw": 30.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 30.0},
    "RP Wind Turbine Mk2 (100 MW)": {"categorie": "Énergie Directe", "mw": 100.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 100.0},
    "RP Wind Turbine Mk3 (150 MW)": {"categorie": "Énergie Directe", "mw": 150.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 150.0},
    "RP Water Turbine Mk1 (Impur 8 MW)": {"categorie": "Énergie Directe", "mw": 8.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 8.0},
    "RP Water Turbine Mk1 (Normal 20 MW)": {"categorie": "Énergie Directe", "mw": 20.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 20.0},
    "RP Water Turbine Mk1 (Pur 50 MW)": {"categorie": "Énergie Directe", "mw": 50.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 50.0},
    "RP Water Dam Section (50 MW / section)": {"categorie": "Énergie Directe", "mw": 50.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 60.0},
    "RP Solar Panel Mk1 (20 MW)": {"categorie": "Énergie Directe", "mw": 20.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 20.0},
    "RP Solar Panel Mk2 (80 MW)": {"categorie": "Énergie Directe", "mw": 80.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 80.0},
    "RP Micro Reactor (1000 MW - Sans Déchet)": {"categorie": "Énergie Directe", "mw": 1000.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 1000.0},
    "RP Modular Reactor (5000 MW @ 100% | 7500 MW @ 150%)": {"categorie": "Énergie Directe", "mw": 5000.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 5000.0},
    "RP Biomass Heater + Boiler Mk1 (500°C ➔ 60 Vapeur)": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 60.0},
    "RP Coal Heater + Boiler Mk1 (500°C ➔ 60 Vapeur)": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 60.0},
    "RP Solution Heater + Boiler Mk2 (750°C Carburant/Turbo ➔ 120 Vapeur)": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 120.0},
    "RP Solution Heater + Boiler Mk2 (1250°C Ionisé ➔ 360 Vapeur)": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 360.0},
    "RP Nuclear Heater + Boiler Mk2 (2000°C ➔ 600 Vapeur)": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 600.0},
    "RP Solar Power Tower (Eau ➔ 120 Vapeur HP)": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 120.0},
    "RP Icarus Receiver (2100 Eau ➔ 1800 Vapeur Compressée)": {"categorie": "Refined Power : Chaudière (Vapeur)", "mw": 100.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 1800.0},
    "RP Turbine Mk1 (60 Vapeur HP ➔ 10 000 RPM)": {"categorie": "Refined Power : Turbine (RPM)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 10000.0},
    "RP Turbine Mk2 (120 Vapeur HP ➔ 25 000 RPM)": {"categorie": "Refined Power : Turbine (RPM)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 25000.0},
    "RP Super HV Turbine (300 Vapeur Comp. ➔ 100 000 RPM)": {"categorie": "Refined Power : Turbine (RPM)", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 100000.0},
    "RP LV Generator (150 MW @ 10 000 RPM | Ratio 0.015)": {"categorie": "Refined Power : Alternateur (RPM ➔ MW)", "mw": 150.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 0.015},
    "RP MV Generator (300 MW @ 17 000 RPM | Ratio 0.01765)": {"categorie": "Refined Power : Alternateur (RPM ➔ MW)", "mw": 300.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 0.01765},
    "RP HV Generator (500 MW @ 25 000 RPM | Ratio 0.02)": {"categorie": "Refined Power : Alternateur (RPM ➔ MW)", "mw": 500.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 0.02},
    "RP Super HV Generator (15 000 MW @ 100 000 RPM | Ratio 0.15)": {"categorie": "Refined Power : Alternateur (RPM ➔ MW)", "mw": 15000.0, "sens_mw": "Produit", "vitesse": 1.0, "somers_max": 0, "valeur_spec": 0.15},
    "RP CO2 Chimney (Évacuation 150 m³/min CO2)": {"categorie": "Production", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 150.0},
    "RP Steam Cooling Tower (Évacuation 300 m³/min Vapeur)": {"categorie": "Production", "mw": 0.0, "vitesse": 1.0, "somers_max": 0, "valeur_spec": 300.0}
}
for k_rp, v_rp in MACHINES_RP_EXACTES.items():
    MACHINES_VANILLA[k_rp] = dict(v_rp)
    MODS_CONFIG["machines_custom"].setdefault(k_rp, dict(v_rp))

def sauvegarder_mods():
    try:
        with open(fichier_mods, "w", encoding="utf-8") as f:
            json.dump(MODS_CONFIG, f, ensure_ascii=False, indent=2)
    except Exception as e:
        popup_error("Erreur Mods", f"Impossible de sauvegarder {fichier_mods} :\n{e}")
def get_machines_par_categorie(cat):
    res = [k for k, v in MODS_CONFIG["machines_custom"].items() if v.get("categorie", "Production") == cat]
    return sorted(res) if res else ["-"]
def est_machine_modifiee_ou_creee(nom_m):
    if nom_m not in MODS_CONFIG["machines_custom"]:
        return False
    if nom_m not in MACHINES_VANILLA:
        return True
    cur = MODS_CONFIG["machines_custom"][nom_m]
    van = MACHINES_VANILLA[nom_m]
    return (
        cur.get("categorie", "Production") != van.get("categorie", "Production") or
        cur.get("sens_mw", "Consomme") != van.get("sens_mw", "Consomme") or
        abs(float(cur.get("mw", 0)) - float(van["mw"])) > 1e-4 or
        abs(float(cur.get("vitesse", 1)) - float(van["vitesse"])) > 1e-4 or
        abs(float(cur.get("valeur_spec", 0)) - float(van.get("valeur_spec", 0))) > 1e-4 or
        int(cur.get("somers_max", 0)) != int(van["somers_max"])
    )
def generer_paliers_cadence():
    max_pct = max(int(MODS_CONFIG.get("max_cadence_pct", 250)), 100)
    if max_pct <= 250:
        return ["0%", "25%", "50%", "75%", "100%", "125%", "150%", "175%", "200%", "225%", "250%"]
    pas = max(25, int(round(max_pct / 10 / 25.0)) * 25)
    vals = list(range(0, max_pct + 1, pas))
    for v_fixe in [100, 250, max_pct]:
        if v_fixe <= max_pct and v_fixe not in vals:
            vals.append(v_fixe)
    return [f"{v}%" for v in sorted(vals)]
ENERGIE_FOREUSE = {"Mk.1": 5.0, "Mk.2": 12.0, "Mk.3": 30.0}
PROD_FOREUSE_BASE = {"Mk.1": 60.0, "Mk.2": 120.0, "Mk.3": 240.0}
MULTIPLICATEUR_PURETE = {"Impur (0.5x)": 0.5, "Normal (1.0x)": 1.0, "Pur (2.0x)": 2.0}
RESSOURCES_EXTRACTION_MAP = {
    "Minerai de fer": "Foreuse", "Minerai de cuivre": "Foreuse", "Calcaire": "Foreuse",
    "Charbon": "Foreuse", "Minerai de catérium": "Foreuse", "Quartz brut": "Foreuse",
    "Soufre": "Foreuse", "Bauxite": "Foreuse", "Uranium": "Foreuse",
    "Minerai d'uranium": "Foreuse", "SAM": "Foreuse", "Eau": "Pompe à eau",
    "Pétrole brut": "Extracteur de pétrole"
}
# ==============================================================================
# 5. FILIÈRES ÉNERGÉTIQUES EN CASCADE
# ==============================================================================
FILIERES_ENERGIE = {
    "🖤 Centrale à Charbon (75 MW)": {
        "puissance_base": 75.0, "conso_gen": [("Charbon", 15.0), ("Eau", 45.0)], "byproducts_gen": [],
        "etapes": [
            {"id": "coal_pump", "nom": "Pompe à eau", "machine": "Pompe à eau", "recette": "Extraction d'Eau", "out_item": "Eau", "out_rate": 120.0, "inputs": [], "byproducts": []},
            {"id": "coal_miner", "nom": "Foreuse Mk.2 (Charbon)", "machine": "Foreuse Mk.2", "recette": "Extraction Charbon", "out_item": "Charbon", "out_rate": 120.0, "inputs": [], "byproducts": []}
        ]
    },
    "⛽ Centrale au Carburant Standard (250 MW)": {
        "puissance_base": 250.0, "conso_gen": [("Carburant", 20.0)], "byproducts_gen": [],
        "etapes": [
            {"id": "fuel_raf", "nom": "Raffinerie (Carburant)", "machine": "Raffinerie", "recette": "Carburant Standard", "out_item": "Carburant", "out_rate": 40.0, "inputs": [("Pétrole brut", 60.0)], "byproducts": [("Résine polymère", 30.0)]},
            {"id": "fuel_oil", "nom": "Extracteur de pétrole", "machine": "Extracteur de pétrole", "recette": "Extraction Pétrole brut", "out_item": "Pétrole brut", "out_rate": 120.0, "inputs": [], "byproducts": []}
        ]
    },
    "💧 Centrale au Carburant Dilué (Optimisé - 250 MW)": {
        "puissance_base": 250.0, "conso_gen": [("Carburant", 20.0)], "byproducts_gen": [],
        "etapes": [
            {"id": "dil_blend", "nom": "Mélangeur (Carburant dilué)", "machine": "Mélangeur", "recette": "Alt : Carburant dilué", "out_item": "Carburant", "out_rate": 100.0, "inputs": [("Résidu d'huile lourde", 50.0), ("Eau", 100.0)], "byproducts": []},
            {"id": "dil_hor", "nom": "Raffinerie (Résidu lourd)", "machine": "Raffinerie", "recette": "Alt : Résidu d'huile lourde", "out_item": "Résidu d'huile lourde", "out_rate": 40.0, "inputs": [("Pétrole brut", 30.0)], "byproducts": [("Résine polymère", 20.0)]},
            {"id": "dil_oil", "nom": "Extracteur de pétrole", "machine": "Extracteur de pétrole", "recette": "Extraction Pétrole brut", "out_item": "Pétrole brut", "out_rate": 120.0, "inputs": [], "byproducts": []},
            {"id": "dil_water", "nom": "Pompe à eau", "machine": "Pompe à eau", "recette": "Extraction d'Eau", "out_item": "Eau", "out_rate": 120.0, "inputs": [], "byproducts": []}
        ]
    },
    "🔥 Centrale au Turbocarburant (250 MW)": {
        "puissance_base": 250.0, "conso_gen": [("Turbocarburant", 7.5)], "byproducts_gen": [],
        "etapes": [
            {"id": "tc_raf_turbo", "nom": "Raffinerie (Turbocarburant)", "machine": "Raffinerie", "recette": "Turbocarburant", "out_item": "Turbocarburant", "out_rate": 18.75, "inputs": [("Carburant", 22.5), ("Charbon compacté", 15.0)], "byproducts": []},
            {"id": "tc_raf_fuel", "nom": "Raffinerie (Carburant)", "machine": "Raffinerie", "recette": "Carburant Standard", "out_item": "Carburant", "out_rate": 40.0, "inputs": [("Pétrole brut", 60.0)], "byproducts": [("Résine polymère", 30.0)]},
            {"id": "tc_ass_coal", "nom": "Assembleuse (Charbon compacté)", "machine": "Assembleuse", "recette": "Charbon compacté", "out_item": "Charbon compacté", "out_rate": 25.0, "inputs": [("Charbon", 25.0), ("Soufre", 25.0)], "byproducts": []},
            {"id": "tc_oil", "nom": "Extracteur de pétrole", "machine": "Extracteur de pétrole", "recette": "Extraction Pétrole brut", "out_item": "Pétrole brut", "out_rate": 120.0, "inputs": [], "byproducts": []},
            {"id": "tc_coal", "nom": "Foreuse Mk.2 (Charbon)", "machine": "Foreuse Mk.2", "recette": "Extraction Charbon", "out_item": "Charbon", "out_rate": 120.0, "inputs": [], "byproducts": []},
            {"id": "tc_sulfur", "nom": "Foreuse Mk.2 (Soufre)", "machine": "Foreuse Mk.2", "recette": "Extraction Soufre", "out_item": "Soufre", "out_rate": 120.0, "inputs": [], "byproducts": []}
        ]
    },
    "🚀 Centrale Nitro Carburant de Fusée (250 MW)": {
        "puissance_base": 250.0, "conso_gen": [("Carburant de fusée", 4.1667)], "byproducts_gen": [],
        "etapes": [
            {"id": "rf_blend_nitro", "nom": "Mélangeur (Nitro Fusée)", "machine": "Mélangeur", "recette": "Alt : Nitro Carburant de fusée", "out_item": "Carburant de fusée", "out_rate": 150.0, "inputs": [("Carburant", 100.0), ("Azote gazeux", 75.0), ("Soufre", 100.0), ("Charbon", 50.0)], "byproducts": [("Charbon compacté", 25.0)]},
            {"id": "rf_blend_dil", "nom": "Mélangeur (Carburant dilué)", "machine": "Mélangeur", "recette": "Alt : Carburant dilué", "out_item": "Carburant", "out_rate": 100.0, "inputs": [("Résidu d'huile lourde", 50.0), ("Eau", 100.0)], "byproducts": []},
            {"id": "rf_raf_hor", "nom": "Raffinerie (Résidu lourd)", "machine": "Raffinerie", "recette": "Alt : Résidu d'huile lourde", "out_item": "Résidu d'huile lourde", "out_rate": 40.0, "inputs": [("Pétrole brut", 30.0)], "byproducts": [("Résine polymère", 20.0)]},
            {"id": "rf_oil", "nom": "Extracteur de pétrole", "machine": "Extracteur de pétrole", "recette": "Extraction Pétrole brut", "out_item": "Pétrole brut", "out_rate": 120.0, "inputs": [], "byproducts": []},
            {"id": "rf_water", "nom": "Pompe à eau", "machine": "Pompe à eau", "recette": "Extraction d'Eau", "out_item": "Eau", "out_rate": 120.0, "inputs": [], "byproducts": []},
            {"id": "rf_sulfur", "nom": "Foreuse Mk.3 (Soufre)", "machine": "Foreuse Mk.3", "recette": "Extraction Soufre", "out_item": "Soufre", "out_rate": 240.0, "inputs": [], "byproducts": []},
            {"id": "rf_coal", "nom": "Foreuse Mk.3 (Charbon)", "machine": "Foreuse Mk.3", "recette": "Extraction Charbon", "out_item": "Charbon", "out_rate": 240.0, "inputs": [], "byproducts": []}
        ]
    },
    "☢️ Centrale Nucléaire Uranium (2500 MW)": {
        "puissance_base": 2500.0, "conso_gen": [("Barre de combustible à l'uranium", 0.2), ("Eau", 240.0)], "byproducts_gen": [("Déchet d'uranium", 10.0)],
        "etapes": [
            {"id": "nuc_mfg_rod", "nom": "Façonneuse (Barre d'uranium)", "machine": "Façonneuse", "recette": "Barre de combustible à l'uranium", "out_item": "Barre de combustible à l'uranium", "out_rate": 0.4, "inputs": [("Cellule d'uranium encapsulée", 20.0), ("Poutre industrielle en béton", 1.2), ("Barre de contrôle électromagnétique", 2.0)], "byproducts": []},
            {"id": "nuc_blend_cell", "nom": "Mélangeur (Cellule d'uranium)", "machine": "Mélangeur", "recette": "Cellule d'uranium encapsulée", "out_item": "Cellule d'uranium encapsulée", "out_rate": 25.0, "inputs": [("Uranium", 50.0), ("Béton", 15.0), ("Acide sulfurique", 30.0)], "byproducts": []},
            {"id": "nuc_raf_acid", "nom": "Raffinerie (Acide sulfurique)", "machine": "Raffinerie", "recette": "Acide sulfurique", "out_item": "Acide sulfurique", "out_rate": 50.0, "inputs": [("Soufre", 50.0), ("Eau", 50.0)], "byproducts": []},
            {"id": "nuc_ass_em", "nom": "Assembleuse (Barre électromagnétique)", "machine": "Assembleuse", "recette": "Barre de contrôle électromagnétique", "out_item": "Barre de contrôle électromagnétique", "out_rate": 4.0, "inputs": [("Stator", 6.0), ("Limiteur d'IA", 4.0)], "byproducts": []},
            {"id": "nuc_ass_eib", "nom": "Assembleuse (Poutre indus. béton)", "machine": "Assembleuse", "recette": "Poutre industrielle en béton", "out_item": "Poutre industrielle en béton", "out_rate": 6.0, "inputs": [("Poutre en acier", 18.0), ("Béton", 36.0)], "byproducts": []},
            {"id": "nuc_pump", "nom": "Pompe à eau (Nucléaire + Acide)", "machine": "Pompe à eau", "recette": "Extraction d'Eau", "out_item": "Eau", "out_rate": 120.0, "inputs": [], "byproducts": []},
            {"id": "nuc_miner_u", "nom": "Foreuse Mk.3 (Uranium)", "machine": "Foreuse Mk.3", "recette": "Extraction Uranium", "out_item": "Uranium", "out_rate": 240.0, "inputs": [], "byproducts": []}
        ]
    }
}
TRADUCTIONS_SECOURS = {
    "Sloppy Alumina": "Alumine baveuse", "Pure Lingot d'aluminium": "Lingot d'aluminium pur",
    "Electrode Rebut d'aluminium": "Rebut d'aluminium (Électrode)", "Instant Scrap": "Rebut instantané",
    "Automated Speed Wiring": "Câblage rapide automatisé", "Classic Batterie": "Batterie classique",
    "Fine Poudre noire": "Poudre noire fine", "Coated Câble": "Câble revêtu",
    "Insulated Câble": "Câble isolé", "Pure Lingot de catérium": "Lingot de catérium pur",
    "Tempered Lingot de catérium": "Lingot de catérium trempé", "Leached Lingot de catérium": "Lingot de catérium lixivié",
    "Electrode Circuit imprimé": "Circuit imprimé (Électrode)", "Fine Béton": "Béton fin",
    "Pure Lingot de cuivre": "Lingot de cuivre pur", "Copper Alloy Ingot": "Lingot d'alliage de cuivre",
    "Tempered Lingot de cuivre": "Lingot de cuivre trempé", "Leached Lingot de cuivre": "Lingot de cuivre lixivié",
    "Insulated Oscillateur à cristal": "Oscillateur à cristal isolé", "Steel Canister": "Bidon en acier",
    "Coated Iron Canister": "Bidon en fer revêtu", "Instant Plutonium Cell": "Cellule de plutonium instantanée",
    "Pure Lingot de fer": "Lingot de fer pur", "Leached Iron ingot": "Lingot de fer lixivié",
    "Basic Lingot de fer": "Lingot de fer basique", "Iron Alloy Ingot": "Lingot d'alliage de fer",
    "Coated Plaque de fer": "Plaque de fer revêtue", "Steel Cast Plate": "Plaque moulée en acier",
    "Steel Rod": "Tige en acier", "Steeled Frame": "Cadre en acier",
    "Automated Miner": "Foreuse automatisée", "Pure Cristal de quartz": "Cristal de quartz pur",
    "Steel Rotor": "Rotor en acier", "Steel Vis": "Vis en acier",
    "Charcoal": "Charbon de bois", "Biocoal": "Biocharbon",
    "Aluminum Rod": "Tige en aluminium", "Cast Vis": "Vis moulée",
    "Aluminum Beam": "Poutre en aluminium", "Iron Pipe": "Tuyau en fer",
    "Caterium Fil électrique": "Fil actif", "Iron Fil électrique": "Fil électrique en fer",
    "Alclad Casing": "Boîtier en aluminium plaqué", "Wet Béton": "Béton humide",
    "Caoutchouc Béton": "Béton de caoutchouc", "Cooling Device": "Dispositif de refroidissement",
    "Steamed Tôle de cuivre": "Tôle de cuivre étuvée", "Oil-Based Diamants": "Diamants à base de pétrole",
    "Oil": "Pétrole", "Dark Matter Trap": "Piège à matière noire",
    "Cristal de matière noirelization": "Cristallisation de matière noire",
    "Turbo Diamants": "Diamants turbo", "Pink Diamants": "Diamants roses",
    "Petroleum Diamants": "Diamants de pétrole", "Cloudy Diamants": "Diamants troubles",
    "Electromagnetic Connection Rod": "Tige de connexion électromagnétique",
    "Encased Industrial Pipe": "Tuyau industriel encapsulé", "Infused Uranium Cell": "Cellule d'uranium infusée",
    "Polyester Tissu": "Tissu en polyester", "Diluted": "Dilué",
    "Heat-Fused Frame": "Cadre fusionné à la chaleur", "Heat Exchanger": "Échangeur de chaleur",
    "Heavy Flexible Frame": "Cadre flexible lourd", "Heavy Encased Frame": "Cadre encapsulé lourd",
    "Silicon": "Silicium", "Dark-Ion": "Ion sombre", "Bolted Frame": "Cadre boulonné",
    "Electric Moteur": "Moteur électrique", "Rigor Moteur": "Moteur de rigueur",
    "Fertile Uranium": "Uranium fertile", "Recycled": "Recyclé",
    "Plutonium Carburant Unit": "Unité de carburant au plutonium", "Quartz Purification": "Purification de quartz",
    "Fused Cristal de quartz": "Cristal de quartz fusionné", "Fused Fil actif": "Fil actif fusionné",
    "Radio Control System": "Système de contrôle radio", "Radio Connection Unit": "Unité de connexion radio",
    "Adhered Plaque de fer": "Plaque de fer collée", "Stitched Plaque de fer": "Plaque de fer cousue",
    "Bolted Plaque de fer": "Plaque de fer boulonnée", "Copper Rotor": "Rotor en cuivre",
    "Distilled Silice": "Silice distillée", "Cheap Silice": "Silice bon marché",
    "Molded Beam": "Poutre moulée", "Coke Lingot d'acier": "Lingot d'acier au coke",
    "Compacted Lingot d'acier": "Lingot d'acier compacté", "Solid Lingot d'acier": "Lingot d'acier solide",
    "Molded Tuyau en acier": "Tuyau en acier moulé", "Super-State Ordinateur": "Ordinateur super-état",
    "OC Superordinateur": "Superordinateur surcadencé", "Turbo Pressure Moteur": "Moteur à pression turbo",
    "Turbo Electric Moteur": "Moteur électrique turbo", "Turbo Heavy Carburant": "Carburant lourd turbo",
    "Turbo Blend Carburant": "Mélange de carburant turbo", "Uranium Ore": "Minerai d'uranium",
    "Uranium Carburant Unit": "Unité de carburant à l'uranium", "Flexible Framework": "Cadre flexible",
    "Fused Fil électrique": "Fil électrique fusionné", "Crystal Ordinateur": "Ordinateur à cristal",
    "Caterium Ordinateur": "Ordinateur en catérium", "Caterium Circuit imprimé": "Circuit imprimé en catérium"
}
# ==============================================================================
# 6. CHARGEMENT DU CSV + FUSION DYNAMIQUE DES MODS
# ==============================================================================
df_base = pd.DataFrame()
df = pd.DataFrame()
liste_machines_prod = []
liste_machines_extraction = []
liste_objets_produits = []
erreur_chargement = ""
ctk.set_appearance_mode(THEME["ctk_mode"])
app = ctk.CTk(fg_color=THEME["bg_main"])
ficsmas_actif = ctk.BooleanVar(value=False)
def charger_et_fusionner_donnees():
    global df_base, df, liste_machines_prod, liste_machines_extraction, liste_objets_produits, erreur_chargement
    try:
        if df_base.empty:
            if not os.path.exists(nom_fichier):
                raise FileNotFoundError(f"Le fichier '{nom_fichier}' est introuvable.")
            raw = pd.read_csv(nom_fichier)
            colonnes_nombres = ['Entrée 1 / Min', 'Entrée 2 / Min', 'Entrée 3 / Min', 'Entrée 4 / Min', 'Sortie 1 / Min', 'Sortie 2 / Min']
            for col in colonnes_nombres:
                raw[col] = raw[col].astype(str).str.replace(r'[\u202f\s]', '', regex=True).str.replace(',', '.', regex=True).astype(float)
            colonnes_texte = ['Nom de la recette', 'Objet de base', 'Bâtiment', 'Entrée 1', 'Entrée 2', 'Entrée 3', 'Entrée 4', 'Sortie 1', 'Sortie 2']
            for eng, fr in TRADUCTIONS_SECOURS.items():
                for col in colonnes_texte:
                    if col in raw.columns:
                        mask = raw[col].notna()
                        raw.loc[mask, col] = raw.loc[mask, col].str.replace(eng, fr, regex=False)
            df_base = raw
        if MODS_CONFIG["recettes_custom"]:
            df_mods = pd.DataFrame(MODS_CONFIG["recettes_custom"])
            df = pd.concat([df_base, df_mods], ignore_index=True)
        else:
            df = df_base.copy()
        df['Est Alternative'] = df['Nom de la recette'].str.contains('Recette alternative', case=False, na=False)
        machines_csv = set(df['Bâtiment'].dropna().unique().tolist())
        machines_prod_cfg = set(k for k, v in MODS_CONFIG["machines_custom"].items() if v.get("categorie", "Production") in ["Production", "Énergie Directe"])
        liste_machines_prod = sorted(list(machines_csv.union(machines_prod_cfg)))
        for k_f in list(FILIERES_ENERGIE.keys()):
            if k_f.startswith("⚡ [Mod] "):
                FILIERES_ENERGIE.pop(k_f, None)
        for m_nom, m_val in MODS_CONFIG["machines_custom"].items():
            if m_val.get("categorie") == "Énergie Directe" or m_val.get("sens_mw") == "Produit":
                mw_p = max(float(m_val.get("mw", 100.0)), 0.1)
                FILIERES_ENERGIE[f"⚡ [Mod] {m_nom} ({mw_p:g} MW)"] = {
                    "puissance_base": mw_p, "conso_gen": [], "byproducts_gen": [], "etapes": []
                }
        ext_custom = [k for k, v in MODS_CONFIG["machines_custom"].items() if v.get("categorie") == "Extraction" and k not in ["Foreuse", "Pompe à eau", "Extracteur de pétrole"]]
        liste_machines_extraction = ["Foreuse", "Pompe à eau", "Extracteur de pétrole"] + sorted(ext_custom)
        mots_noel = ["ficsmas", "neige", "étoile", "boule", "sucre", "couronne", "cadeau", "branche"]
        objets_bruts = sorted(df['Sortie 1'].dropna().unique().tolist())
        if not ficsmas_actif.get():
            objets_bruts = [o for o in objets_bruts if not any(m in str(o).lower() for m in mots_noel)]
        liste_objets_produits = objets_bruts
    except Exception as e:
        erreur_chargement = str(e)
charger_et_fusionner_donnees()
# ==============================================================================
# 7. INITIALISATION DE LA FENÊTRE & PERSISTANCE PAR DOSSIERS D'USINES
# ==============================================================================
app.geometry("1900x1030")
app.title(f"{NOM_LOGICIEL} — MULTI-USINES, REFINED POWER, DIGITAL STORAGE & MODS")
if os.path.exists(chemin_icone):
    try:
        app.iconbitmap(chemin_icone)
    except Exception:
        pass
if erreur_chargement:
    ctk.CTkLabel(app, text="⚠️ ERREUR CRITIQUE : CSV INTROUVABLE", font=ctk.CTkFont(size=24, weight="bold"), text_color=THEME["status_err"]).pack(pady=50)
    ctk.CTkLabel(app, text=erreur_chargement, font=ctk.CTkFont(size=15)).pack(pady=10)
    app.mainloop()
    exit()
def creer_structure_usine_vide():
    return {
        "ateliers": [],
        "foreuses": [],
        "parcs_energie": [],
        "refined_power": [],
        "digital_storage": {
            "equipements": [
                {"type": "Contrôleur Réseau Central", "qte": "1", "mw_unit": "50.0", "capacite_items": "0", "bande_passante": "600"},
                {"type": "Baie de Disques + Disques 16k", "qte": "2", "mw_unit": "25.0", "capacite_items": "16000", "bande_passante": "1200"}
            ],
            "flux_cloud": []
        }
    }
def sauvegarder_usine_dans_son_dossier(nom_usine, data_u):
    """Enregistre les fichiers séparés dans Documents/Nexus_Industrial_Architect/Usines/<Nom_Usine>/"""
    try:
        d_usine = obtenir_dossier_usine(nom_usine)
        with open(os.path.join(d_usine, "meta_usine.json"), "w", encoding="utf-8") as f:
            json.dump({"nom_exact": nom_usine}, f, ensure_ascii=False, indent=2)
        with open(os.path.join(d_usine, "ateliers.json"), "w", encoding="utf-8") as f:
            json.dump(data_u.get("ateliers", []), f, ensure_ascii=False, indent=2)
        with open(os.path.join(d_usine, "foreuses.json"), "w", encoding="utf-8") as f:
            json.dump(data_u.get("foreuses", []), f, ensure_ascii=False, indent=2)
        with open(os.path.join(d_usine, "energie.json"), "w", encoding="utf-8") as f:
            json.dump({
                "parcs_energie": data_u.get("parcs_energie", []),
                "refined_power": data_u.get("refined_power", [])
            }, f, ensure_ascii=False, indent=2)
        with open(os.path.join(d_usine, "digital_storage.json"), "w", encoding="utf-8") as f:
            json.dump(data_u.get("digital_storage", creer_structure_usine_vide()["digital_storage"]), f, ensure_ascii=False, indent=2)
    except Exception:
        pass
def charger_toutes_les_usines_depuis_documents():
    usines = {}
    if os.path.exists(DOSSIER_TOUTES_USINES):
        for entry in sorted(os.listdir(DOSSIER_TOUTES_USINES)):
            che_d = os.path.join(DOSSIER_TOUTES_USINES, entry)
            if os.path.isdir(che_d):
                nom_u = entry
                f_meta = os.path.join(che_d, "meta_usine.json")
                if os.path.exists(f_meta):
                    try:
                        with open(f_meta, "r", encoding="utf-8") as f:
                            nom_u = json.load(f).get("nom_exact", entry)
                    except Exception:
                        pass
                u_obj = creer_structure_usine_vide()
                for f_nom, cle in [("ateliers.json", "ateliers"), ("foreuses.json", "foreuses")]:
                    p_f = os.path.join(che_d, f_nom)
                    if os.path.exists(p_f):
                        try:
                            with open(p_f, "r", encoding="utf-8") as f:
                                u_obj[cle] = json.load(f)
                        except Exception:
                            pass
                p_en = os.path.join(che_d, "energie.json")
                if os.path.exists(p_en):
                    try:
                        with open(p_en, "r", encoding="utf-8") as f:
                            en_d = json.load(f)
                            if isinstance(en_d, dict):
                                u_obj["parcs_energie"] = en_d.get("parcs_energie", [])
                                u_obj["refined_power"] = en_d.get("refined_power", [])
                    except Exception:
                        pass
                p_ds = os.path.join(che_d, "digital_storage.json")
                if os.path.exists(p_ds):
                    try:
                        with open(p_ds, "r", encoding="utf-8") as f:
                            u_obj["digital_storage"] = json.load(f)
                    except Exception:
                        pass
                usines[nom_u] = u_obj
    if not usines:
        u_def = creer_structure_usine_vide()
        u_def["ateliers"].append({"machine": "Constructeur", "type": "Standard", "recette": "", "qte": "1", "cadence": "100", "somers": "0"})
        u_def["foreuses"].append({"machine": "Foreuse", "tier": "Mk.2", "purete": "Normal (1.0x)", "ressource": "Minerai de fer", "qte": "1", "cadence": "100", "somers": "0"})
        u_def["parcs_energie"].append({
            "filiere": "⛽ Centrale au Carburant Standard (250 MW)", "mode": "Auto-Compensation Déficit",
            "portee_auto": "Réseau Global", "nb_fixe": "4", "cadence_gen": "100",
            "boucle_auto": True, "actif": True, "cadences_etapes": {}, "qtes_etapes": {}
        })
        usines["Usine Principale"] = u_def
        sauvegarder_usine_dans_son_dossier("Usine Principale", u_def)
    return usines
usines_data = charger_toutes_les_usines_depuis_documents()
usine_active_nom = USER_SETTINGS.get("derniere_usine_active", list(usines_data.keys())[0])
if usine_active_nom not in usines_data:
    usine_active_nom = list(usines_data.keys())[0]
verrou_chargement_ui = False
job_calcul_debounce = None
cartes_ateliers = []
cartes_foreuses = []
cartes_parcs_energie = []
cartes_refined_power = []
cartes_ds_equip = []
cartes_ds_flux = []
dernier_flux_calcule_usine = {}
dernier_flux_calcule_global = {}
dernier_deficit_mw_usine = 0.0
dernier_deficit_mw_global = 0.0
preferences_recettes_auto = {}
lbl_resume_machines = None
lbl_cout_construction = None
portee_bilan_var = ctk.StringVar(value="🌐 Toutes Usines")
filtre_bilan_var = ctk.StringVar(value="Tous")
mode_affichage_cartes = ctk.StringVar(value=USER_SETTINGS.get("mode_affichage_cartes", "Cartes"))
if mode_affichage_cartes.get() not in ("Ligne", "Cartes"):
    mode_affichage_cartes.set("Cartes")

def ajouter_bouton_aide(parent, message):
    ctk.CTkButton(
        parent, text="?", width=22, height=22, corner_radius=11,
        fg_color=THEME["bg_panel"], hover_color=THEME["seg_sel"],
        text_color=THEME["text_main"], command=lambda: popup_info("Petite aide", message)
    ).pack(side="left", padx=4)

def planifier_calcul(delai_ms=450):
    """Anti-rebond (Debounce) : empêche toute perte de focus pendant la frappe rapide dans les champs Qté."""
    global job_calcul_debounce
    if verrou_chargement_ui:
        return
    if job_calcul_debounce is not None:
        try:
            app.after_cancel(job_calcul_debounce)
        except Exception:
            pass
    job_calcul_debounce = app.after(delai_ms, declencher_calcul)
def get_machine_specs(nom_machine):
    if nom_machine in MODS_CONFIG["machines_custom"]:
        return MODS_CONFIG["machines_custom"][nom_machine]
    return {"categorie": "Production", "mw": 15.0, "vitesse": 1.0, "somers_max": 1, "valeur_spec": 0.0}
def calculer_eclats_machine(cadence_pct):
    if cadence_pct <= 100.0:
        return 0
    pas = max(float(MODS_CONFIG.get("gain_par_eclat_pct", 50.0)), 1.0)
    return math.ceil((cadence_pct - 100.0) / pas)
def calculer_multiplicateurs_somers(s_used, s_max):
    if s_max <= 0 or s_used <= 0:
        return 1.0, 1.0
    ratio = min(float(s_used) / float(s_max), 1.0)
    bonus_max = float(MODS_CONFIG.get("bonus_prod_somersloop_pct", 100.0)) / 100.0
    exp_elec = float(MODS_CONFIG.get("exposant_elec_somersloop", 2.0))
    return 1.0 + (ratio * bonus_max), (1.0 + ratio * bonus_max) ** exp_elec

def ajouter_compteur_machine(compteurs, nom, nombre):
    if nom and nombre > 0:
        compteurs[nom] = compteurs.get(nom, 0) + nombre

def compter_machines_usine(usine):
    compteurs = {}
    for atelier in usine.get("ateliers", []):
        try:
            nombre = max(int(atelier.get("qte", "0")), 0)
        except (TypeError, ValueError):
            continue
        ajouter_compteur_machine(compteurs, atelier.get("machine", "Constructeur"), nombre)
    for extracteur in usine.get("foreuses", []):
        try:
            nombre = max(int(extracteur.get("qte", "0")), 0)
        except (TypeError, ValueError):
            continue
        machine = extracteur.get("machine", "Foreuse")
        nom = f"{machine} {extracteur.get('tier', 'Mk.2')}" if machine == "Foreuse" else machine
        ajouter_compteur_machine(compteurs, nom, nombre)
    ds_config = usine.get("digital_storage", {})
    for equipement in ds_config.get("equipements", []):
        try:
            quantite = max(int(equipement.get("qte", "0")), 0)
        except (TypeError, ValueError):
            continue
        ajouter_compteur_machine(compteurs, equipement.get("type", "Équipement Digital Storage"), quantite)
        serveurs = equipement.get("serveurs", {})
        for nom_serveur in DS_SERVEURS:
            ancien_nom = next((alias for alias, nouveau in DS_ALIAS_SERVEURS.items() if nouveau == nom_serveur), None)
            try:
                nombre = max(int(serveurs.get(nom_serveur, serveurs.get(ancien_nom, "0"))), 0)
            except (TypeError, ValueError):
                nombre = 0
            ajouter_compteur_machine(compteurs, nom_serveur, nombre * quantite)
    return compteurs, sum(compteurs.values())

def organiser_cartes_grille(cartes, conteneur):
    colonnes = 2 if mode_affichage_cartes.get() == "Cartes" else 1
    for colonne in range(2):
        conteneur.grid_columnconfigure(colonne, weight=1 if colonne < colonnes else 0)
    for index, carte in enumerate(cartes):
        carte.grid(
            row=index // colonnes, column=index % colonnes,
            sticky="nsew", padx=6, pady=6
        )

class FrameDefilantOptimise(ctk.CTkScrollableFrame):
    def __init__(self, *args, **kwargs):
        self._scroll_delta_pending = {"x": 0, "y": 0}
        self._scroll_job = None
        self._barre_scroll_args = None
        self._barre_scroll_job = None
        super().__init__(*args, **kwargs)
        self._scrollbar.configure(command=self._planifier_defilement_barre)

    def _mouse_wheel_all(self, event):
        if not self._check_if_valid_scroll(event.widget):
            return

        axe = "x" if self._shift_pressed else "y"
        if sys.platform.startswith("win") or sys.platform == "darwin":
            self._scroll_delta_pending[axe] += event.delta
        elif sys.platform.startswith("linux"):
            self._scroll_delta_pending[axe] += -1 if event.num == 4 else 1

        if self._scroll_job is None:
            self._scroll_job = self.after(16, self._appliquer_defilement)

    def _appliquer_defilement(self):
        self._scroll_job = None
        for axe, delta in self._scroll_delta_pending.items():
            self._scroll_delta_pending[axe] = 0
            if sys.platform.startswith("win"):
                pas = -int(delta / 6)
            elif sys.platform == "darwin":
                pas = -delta
            else:
                pas = delta
            if pas:
                vue = self._parent_canvas.xview() if axe == "x" else self._parent_canvas.yview()
                if vue != (0.0, 1.0):
                    self._parent_canvas.xview("scroll", pas, "units") if axe == "x" else self._parent_canvas.yview("scroll", pas, "units")

    def _planifier_defilement_barre(self, *args):
        self._barre_scroll_args = args
        if self._barre_scroll_job is None:
            self._barre_scroll_job = self.after(16, self._appliquer_defilement_barre)

    def _appliquer_defilement_barre(self):
        self._barre_scroll_job = None
        args = self._barre_scroll_args
        self._barre_scroll_args = None
        if args is not None:
            self._parent_canvas.yview(*args)

    def destroy(self):
        for attribute in ("_scroll_job", "_barre_scroll_job"):
            job = getattr(self, attribute)
            if job is not None:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
                setattr(self, attribute, None)
        super().destroy()

# ==============================================================================
# 8. CARTES MODULAIRES : ATELIERS, FOREUSES, PARCS ÉNERGIE, REFINED POWER & DIGITAL STORAGE
# ==============================================================================
class CarteAtelierModulaire(ctk.CTkFrame):
    def __init__(self, master, numero, init_data=None):
        super().__init__(master, fg_color=THEME["bg_card"], border_color=THEME["border"], border_width=1, corner_radius=10)
        self.numero = numero
        paliers = generer_paliers_cadence()
        top_bar = ctk.CTkFrame(self, fg_color=THEME["bg_card"])
        top_bar.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(top_bar, text=f"ATELIER #{numero:02d}", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), fg_color=THEME["tab_sel"], text_color="#FFFFFF", corner_radius=6, padx=8, pady=4).pack(side="left", padx=(0, 8))
        self.ent_nom = ctk.CTkEntry(top_bar, width=160, placeholder_text="Nom personnalisé", fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"])
        self.ent_nom.pack(side="left", padx=(0, 8))
        self.ent_nom.bind("<KeyRelease>", self.on_nom_change)
        ctk.CTkButton(top_bar, text="✕ RETIRER", width=85, height=28, corner_radius=8, fg_color="#991B1B", hover_color="#7F1D1D", text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), command=self.supprimer).pack(side="right", padx=(4, 8))
        self.btn_details = ctk.CTkButton(top_bar, text="⌃ Détails", width=82, height=28, corner_radius=8, fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"], command=self.basculer_details)
        self.btn_details.pack(side="right", padx=(4, 8))
        resume_bar = ctk.CTkFrame(self, fg_color=THEME["bg_card"])
        resume_bar.pack(fill="x", padx=12, pady=(0, 4))
        self.lbl_resume_carte = ctk.CTkLabel(resume_bar, text="", anchor="w", text_color=THEME["text_muted"])
        self.lbl_resume_carte.pack(fill="x", padx=4)
        self.frame_details = ctk.CTkFrame(self, fg_color=THEME["bg_card"])
        self.frame_details.pack(fill="x")
        self._details_ouverts = True
        detail_bar = ctk.CTkFrame(self.frame_details, fg_color=THEME["bg_card"])
        detail_bar.pack(fill="x", padx=12, pady=(0, 4))
        row_machine = ctk.CTkFrame(detail_bar, fg_color=THEME["bg_card"])
        row_machine.pack(fill="x")
        row_recipe = ctk.CTkFrame(detail_bar, fg_color=THEME["bg_card"])
        row_recipe.pack(fill="x", pady=(4, 0))
        ctk.CTkLabel(row_machine, text="Bâtiment :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_muted"]).pack(side="left", padx=(0, 4))
        self.menu_machine = ctk.CTkOptionMenu(row_machine, values=liste_machines_prod, width=165, fg_color=THEME["bg_card_alt"], button_color=THEME["tab_sel"], text_color=THEME["text_main"], command=self.on_machine_change)
        self.menu_machine.pack(side="left", padx=(0, 10))
        self.seg_type = ctk.CTkSegmentedButton(row_machine, values=["Standard", "Alternative"], fg_color=THEME["bg_card_alt"], selected_color=THEME["seg_sel"], text_color="#FFFFFF", command=self.update_recettes)
        self.seg_type.set("Standard")
        self.seg_type.pack(side="left", padx=(0, 4))
        ctk.CTkLabel(row_recipe, text="Recette :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_muted"]).pack(side="left", padx=(0, 4))
        self.menu_recette = ctk.CTkComboBox(row_recipe, values=["-"], fg_color=THEME["bg_card_alt"], border_color=THEME["border"], button_color=THEME["seg_sel"], text_color=THEME["text_main"], command=self.on_recette_change)
        self.menu_recette.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.menu_recette.bind("<KeyRelease>", lambda _: planifier_calcul())
        self.lbl_recette_details = ctk.CTkLabel(self.frame_details, text="", justify="left", anchor="w", wraplength=1050, text_color=THEME["text_muted"], font=ctk.CTkFont(size=11))
        self.lbl_recette_details.pack(fill="x", padx=14, pady=(0, 3))
        mid_bar = ctk.CTkFrame(self.frame_details, fg_color=THEME["bg_card_alt"], corner_radius=8)
        mid_bar.pack(fill="x", padx=12, pady=4)
        row_controls = ctk.CTkFrame(mid_bar, fg_color=THEME["bg_card_alt"])
        row_controls.pack(fill="x", padx=6, pady=(5, 2))
        row_cadence = ctk.CTkFrame(mid_bar, fg_color=THEME["bg_card_alt"])
        row_cadence.pack(fill="x", padx=8, pady=(0, 5))
        ajouter_bouton_aide(row_controls, "La quantité indique combien de bâtiments tu as. La cadence fait aller la machine plus ou moins vite. Les Somersloops donnent plus de production, mais prennent des emplacements dans cette machine.")
        ctk.CTkLabel(row_controls, text="Qté :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(4, 4), pady=5)
        ctk.CTkButton(row_controls, text="-", width=30, height=28, corner_radius=6, fg_color="#334155", text_color="#FFFFFF", command=lambda: self.ajuster_qte(-1)).pack(side="left", padx=2)
        self.entree_qte = ctk.CTkEntry(row_controls, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.entree_qte.pack(side="left", padx=2, pady=4)
        self.entree_qte.insert(0, "1")
        self.entree_qte.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkButton(row_controls, text="+", width=30, height=28, corner_radius=6, fg_color=THEME["tab_sel"], text_color="#FFFFFF", command=lambda: self.ajuster_qte(1)).pack(side="left", padx=(2, 12))
        ctk.CTkLabel(row_controls, text="Cadence (%) :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(0, 4))
        self.entree_cadence = ctk.CTkEntry(row_controls, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
        self.entree_cadence.pack(side="left", padx=3, pady=4)
        self.entree_cadence.insert(0, "100")
        self.entree_cadence.bind("<KeyRelease>", self.on_manual_surc)
        ctk.CTkLabel(row_controls, text="🌀 Somersloops :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
        self.seg_somers = ctk.CTkSegmentedButton(row_controls, values=["0", "1"], fg_color=THEME["bg_panel"], selected_color=THEME["accent_purple"], text_color="#FFFFFF", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), command=lambda _: declencher_calcul())
        self.seg_somers.set("0")
        self.seg_somers.pack(side="left", padx=(0, 4), pady=4)
        self.seg_surc = ctk.CTkSegmentedButton(row_cadence, values=paliers, fg_color=THEME["bg_panel"], selected_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), command=self.on_quick_surc)
        self.seg_surc.set("100%")
        self.seg_surc.pack(fill="x", padx=2, pady=2)
        self.lbl_telemetrie = ctk.CTkLabel(self.frame_details, text="⚡ 0.0 MW  |  🔋 0 Éclat  |  🌀 Prod x1.00", font=ctk.CTkFont(family="Consolas", size=12), text_color=THEME["text_muted"], anchor="w")
        self.lbl_telemetrie.pack(fill="x", padx=14, pady=(2, 8))
        if init_data:
            m_init = init_data.get("machine", liste_machines_prod[0] if liste_machines_prod else "Constructeur")
            self.menu_machine.set(m_init if m_init in liste_machines_prod else (liste_machines_prod[0] if liste_machines_prod else "Constructeur"))
            self.seg_type.set(init_data.get("type", "Standard"))
            self.on_machine_change(declencher=False)
            if init_data.get("recette"):
                self.menu_recette.set(init_data["recette"])
            self.entree_qte.delete(0, "end")
            self.entree_qte.insert(0, str(init_data.get("qte", "1")))
            self.entree_cadence.delete(0, "end")
            self.entree_cadence.insert(0, str(init_data.get("cadence", "100")))
            cad_txt = f"{init_data.get('cadence', '100')}%"
            if cad_txt in paliers:
                self.seg_surc.set(cad_txt)
            s_val = str(init_data.get("somers", "0"))
            if s_val in self.seg_somers.cget("values"):
                self.seg_somers.set(s_val)
        else:
            self.menu_machine.set(liste_machines_prod[0] if liste_machines_prod else "Constructeur")
            self.on_machine_change(declencher=False)
        if init_data and init_data.get("nom"):
            self.ent_nom.insert(0, str(init_data["nom"]))
        self.maj_resume_carte()
        if mode_affichage_cartes.get() == "Ligne":
            self.basculer_details(False)
    def nom_affiche(self):
        return self.ent_nom.get().strip() or f"Atelier #{self.numero:02d}"
    def maj_resume_carte(self):
        self.lbl_resume_carte.configure(text=f"{self.nom_affiche()} • {self.menu_machine.get()} • {self.menu_recette.get()}")
        recette_trouvee = df[df["Nom de la recette"] == self.menu_recette.get()]
        if recette_trouvee.empty:
            self.lbl_recette_details.configure(text="Choisis une recette pour voir les matériaux utilisés.")
            return
        recette = recette_trouvee.iloc[0]
        entrees = []
        sorties = []
        for index in range(1, 5):
            nom = recette.get(f"Entrée {index}")
            quantite = recette.get(f"Entrée {index} / Min")
            if pd.notna(nom) and pd.notna(quantite) and float(quantite) > 0:
                entrees.append(f"{float(quantite):g} {nom}/min")
        for index in range(1, 3):
            nom = recette.get(f"Sortie {index}")
            quantite = recette.get(f"Sortie {index} / Min")
            if pd.notna(nom) and pd.notna(quantite) and float(quantite) > 0:
                sorties.append(f"{float(quantite):g} {nom}/min")
        self.lbl_recette_details.configure(text=f"IN : {' + '.join(entrees) or 'rien'}   ➜   OUT : {' + '.join(sorties) or 'rien'}")
    def on_nom_change(self, _=None):
        self.maj_resume_carte()
        planifier_calcul()
    def basculer_details(self, force=None):
        self._details_ouverts = not self._details_ouverts if force is None else force
        if self._details_ouverts:
            self.frame_details.pack(fill="x")
            self.btn_details.configure(text="⌃ Détails")
        else:
            self.frame_details.pack_forget()
            self.btn_details.configure(text="⌄ Détails")
    def ajuster_qte(self, delta):
        try:
            v = int(self.entree_qte.get().strip())
        except ValueError:
            v = 1
        nv = max(0, v + delta)
        self.entree_qte.delete(0, "end")
        self.entree_qte.insert(0, str(nv))
        declencher_calcul()
    def on_quick_surc(self, val):
        self.entree_cadence.delete(0, "end")
        self.entree_cadence.insert(0, val.replace("%", ""))
        declencher_calcul()
    def on_manual_surc(self, _=None):
        txt = self.entree_cadence.get().strip().replace("%", "")
        if f"{txt}%" in generer_paliers_cadence():
            self.seg_surc.set(f"{txt}%")
        planifier_calcul()
    def on_machine_change(self, _=None, declencher=True):
        machine = self.menu_machine.get()
        s_max = int(get_machine_specs(machine).get("somers_max", 1))
        vals = [str(i) for i in range(max(s_max, 0) + 1)]
        cur = self.seg_somers.get()
        self.seg_somers.configure(values=vals)
        self.seg_somers.set(cur if cur in vals else "0")
        self.update_recettes(declencher=declencher)
    def update_recettes(self, _=None, declencher=True):
        machine = self.menu_machine.get()
        type_recette = self.seg_type.get()
        df_m = df[df['Bâtiment'] == machine]
        df_f = df_m[~df_m['Est Alternative']] if type_recette == "Standard" else df_m[df_m['Est Alternative']]
        recettes = df_f['Nom de la recette'].tolist()
        if not ficsmas_actif.get():
            mots_noel = ["ficsmas", "neige", "étoile", "boule", "sucre", "couronne", "cadeau", "branche"]
            recettes = [r for r in recettes if not any(m in str(r).lower() for m in mots_noel)]
        if not recettes:
            recettes = ["Aucune recette"]
        cur_rec = self.menu_recette.get()
        self.menu_recette.configure(values=recettes)
        self.menu_recette.set(cur_rec if cur_rec in recettes else recettes[0])
        self.maj_resume_carte()
        if declencher:
            declencher_calcul()
    def on_recette_change(self, _=None):
        self.maj_resume_carte()
        declencher_calcul()
    def exporter_dict(self):
        return {
            "machine": self.menu_machine.get(), "type": self.seg_type.get(),
            "recette": self.menu_recette.get(), "qte": self.entree_qte.get().strip(),
            "cadence": self.entree_cadence.get().strip().replace("%", ""), "somers": self.seg_somers.get(),
            "nom": self.ent_nom.get().strip()
        }
    def supprimer(self):
        if self in cartes_ateliers:
            cartes_ateliers.remove(self)
        self.destroy()
        organiser_cartes_grille(cartes_ateliers, scroll_ateliers)
        declencher_calcul()
class CarteForeuseModulaire(ctk.CTkFrame):
    def __init__(self, master, numero, init_data=None):
        super().__init__(master, fg_color=THEME["bg_card"], border_color=THEME["border"], border_width=1, corner_radius=10)
        self.numero = numero
        paliers = generer_paliers_cadence()
        top_bar = ctk.CTkFrame(self, fg_color=THEME["bg_card"])
        top_bar.pack(fill="x", padx=12, pady=(10, 6))
        ctk.CTkLabel(top_bar, text=f"EXTRACTEUR #{numero:02d}", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), fg_color=THEME["seg_sel"], text_color="#FFFFFF", corner_radius=6, padx=8, pady=4).pack(side="left", padx=(0, 8))
        self.ent_nom = ctk.CTkEntry(top_bar, width=160, placeholder_text="Nom personnalisé", fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"])
        self.ent_nom.pack(side="left", padx=(0, 8))
        self.ent_nom.bind("<KeyRelease>", self.maj_resume_carte)
        ctk.CTkButton(top_bar, text="✕ RETIRER", width=85, height=28, corner_radius=8, fg_color="#991B1B", hover_color="#7F1D1D", text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), command=self.supprimer).pack(side="right", padx=(4, 8))
        self.btn_details = ctk.CTkButton(top_bar, text="⌃ Détails", width=82, height=28, corner_radius=8, fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"], command=self.basculer_details)
        self.btn_details.pack(side="right", padx=(4, 8))
        resume_bar = ctk.CTkFrame(self, fg_color=THEME["bg_card"])
        resume_bar.pack(fill="x", padx=12, pady=(0, 4))
        self.lbl_resume_carte = ctk.CTkLabel(resume_bar, text="", anchor="w", text_color=THEME["text_muted"])
        self.lbl_resume_carte.pack(fill="x", padx=4)
        self.frame_details = ctk.CTkFrame(self, fg_color=THEME["bg_card"])
        self.frame_details.pack(fill="x")
        self._details_ouverts = True
        detail_bar = ctk.CTkFrame(self.frame_details, fg_color=THEME["bg_card"])
        detail_bar.pack(fill="x", padx=12, pady=(0, 4))
        row_machine = ctk.CTkFrame(detail_bar, fg_color=THEME["bg_card"])
        row_machine.pack(fill="x")
        row_resource = ctk.CTkFrame(detail_bar, fg_color=THEME["bg_card"])
        row_resource.pack(fill="x", pady=(4, 0))
        self.menu_machine = ctk.CTkOptionMenu(row_machine, values=liste_machines_extraction, width=175, fg_color=THEME["bg_card_alt"], button_color=THEME["seg_sel"], text_color=THEME["text_main"], command=self.update_options)
        self.menu_machine.pack(side="left", padx=(0, 10))
        self.menu_machine.set("Foreuse")
        self.seg_tier = ctk.CTkSegmentedButton(row_machine, values=["Mk.1", "Mk.2", "Mk.3"], fg_color=THEME["bg_card_alt"], selected_color=THEME["tab_sel"], text_color="#FFFFFF", command=self.maj_resume_carte)
        self.seg_tier.set("Mk.2")
        self.seg_tier.pack(side="left", padx=(0, 10))
        self.seg_purete = ctk.CTkSegmentedButton(row_machine, values=["Impur (0.5x)", "Normal (1.0x)", "Pur (2.0x)"], fg_color=THEME["bg_card_alt"], selected_color=THEME["seg_sel"], text_color="#FFFFFF", command=self.maj_resume_carte)
        self.seg_purete.set("Normal (1.0x)")
        self.seg_purete.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.minerais = ["Minerai de fer", "Minerai de cuivre", "Calcaire", "Charbon", "Minerai de catérium", "Quartz brut", "Soufre", "Bauxite", "Uranium", "SAM", "Eau", "Pétrole brut", "Azote gazeux"]
        self.menu_ressource = ctk.CTkComboBox(row_resource, values=self.minerais, fg_color=THEME["bg_card_alt"], border_color=THEME["border"], button_color=THEME["tab_sel"], text_color=THEME["text_main"], command=self.maj_resume_carte)
        self.menu_ressource.pack(fill="x", expand=True, padx=(0, 4))
        mid_bar = ctk.CTkFrame(self.frame_details, fg_color=THEME["bg_card_alt"], corner_radius=8)
        mid_bar.pack(fill="x", padx=12, pady=4)
        row_controls = ctk.CTkFrame(mid_bar, fg_color=THEME["bg_card_alt"])
        row_controls.pack(fill="x", padx=6, pady=(5, 2))
        row_cadence = ctk.CTkFrame(mid_bar, fg_color=THEME["bg_card_alt"])
        row_cadence.pack(fill="x", padx=8, pady=(0, 5))
        ajouter_bouton_aide(row_controls, "La quantité indique combien d'extracteurs tu as. La pureté du gisement et la cadence changent la quantité de ressource récupérée. Les foreuses n'ont pas d'emplacement Somersloop.")
        ctk.CTkLabel(row_controls, text="Qté :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(4, 4), pady=5)
        ctk.CTkButton(row_controls, text="-", width=30, height=28, corner_radius=6, fg_color="#334155", text_color="#FFFFFF", command=lambda: self.ajuster_qte(-1)).pack(side="left", padx=2)
        self.entree_qte = ctk.CTkEntry(row_controls, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.entree_qte.pack(side="left", padx=2, pady=4)
        self.entree_qte.insert(0, "1")
        self.entree_qte.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkButton(row_controls, text="+", width=30, height=28, corner_radius=6, fg_color=THEME["tab_sel"], text_color="#FFFFFF", command=lambda: self.ajuster_qte(1)).pack(side="left", padx=(2, 12))
        ctk.CTkLabel(row_controls, text="Cadence (%) :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(0, 4))
        self.entree_cadence = ctk.CTkEntry(row_controls, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
        self.entree_cadence.pack(side="left", padx=3, pady=4)
        self.entree_cadence.insert(0, "100")
        self.entree_cadence.bind("<KeyRelease>", self.on_manual_surc)
        self.seg_surc = ctk.CTkSegmentedButton(row_cadence, values=paliers, fg_color=THEME["bg_panel"], selected_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), command=self.on_quick_surc)
        self.seg_surc.set("100%")
        self.seg_surc.pack(fill="x", padx=2, pady=2)
        self.seg_somers = ctk.CTkSegmentedButton(mid_bar, values=["0"], fg_color=THEME["bg_panel"], selected_color=THEME["accent_purple"], text_color="#FFFFFF", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), state="disabled", command=lambda _: declencher_calcul())
        self.seg_somers.set("0")
        self.lbl_telemetrie = ctk.CTkLabel(self.frame_details, text="⚡ 0.0 MW  |  🔋 0 Éclat  |  Débit extrait : +0.0 / min", font=ctk.CTkFont(family="Consolas", size=12), text_color=THEME["text_muted"], anchor="w")
        self.lbl_telemetrie.pack(fill="x", padx=14, pady=(2, 8))
        if init_data:
            self.menu_machine.set(init_data.get("machine", "Foreuse"))
            self.update_options(declencher=False)
            self.seg_tier.set(init_data.get("tier", "Mk.2"))
            self.seg_purete.set(init_data.get("purete", "Normal (1.0x)"))
            if init_data.get("ressource"):
                self.menu_ressource.set(init_data["ressource"])
            self.entree_qte.delete(0, "end")
            self.entree_qte.insert(0, str(init_data.get("qte", "1")))
            self.entree_cadence.delete(0, "end")
            self.entree_cadence.insert(0, str(init_data.get("cadence", "100")))
            cad_txt = f"{init_data.get('cadence', '100')}%"
            if cad_txt in paliers:
                self.seg_surc.set(cad_txt)
            self.seg_somers.set("0")
        else:
            self.update_options(declencher=False)
        if init_data and init_data.get("nom"):
            self.ent_nom.insert(0, str(init_data["nom"]))
        self.maj_resume_carte()
        if mode_affichage_cartes.get() == "Ligne":
            self.basculer_details(False)
    def nom_affiche(self):
        return self.ent_nom.get().strip() or f"Extracteur #{self.numero:02d}"
    def maj_resume_carte(self, _=None):
        text = f"{self.nom_affiche()} • {self.menu_machine.get()} • {self.menu_ressource.get()}"
        if self.menu_machine.get() == "Foreuse":
            text = f"{text} • {self.seg_tier.get()} • {self.seg_purete.get()}"
        self.lbl_resume_carte.configure(text=text)
        declencher_calcul()
    def basculer_details(self, force=None):
        self._details_ouverts = not self._details_ouverts if force is None else force
        if self._details_ouverts:
            self.frame_details.pack(fill="x")
            self.btn_details.configure(text="⌃ Détails")
        else:
            self.frame_details.pack_forget()
            self.btn_details.configure(text="⌄ Détails")
    def ajuster_qte(self, delta):
        try:
            v = int(self.entree_qte.get().strip())
        except ValueError:
            v = 1
        self.entree_qte.delete(0, "end")
        self.entree_qte.insert(0, str(max(0, v + delta)))
        declencher_calcul()
    def on_quick_surc(self, val):
        self.entree_cadence.delete(0, "end")
        self.entree_cadence.insert(0, val.replace("%", ""))
        declencher_calcul()
    def on_manual_surc(self, _=None):
        txt = self.entree_cadence.get().strip().replace("%", "")
        if f"{txt}%" in generer_paliers_cadence():
            self.seg_surc.set(f"{txt}%")
        planifier_calcul()
    def update_options(self, _=None, declencher=True):
        m = self.menu_machine.get()
        if m == "Foreuse":
            self.seg_tier.configure(state="normal")
            self.seg_purete.configure(state="normal")
        elif m == "Pompe à eau":
            self.seg_tier.configure(state="disabled")
            self.seg_purete.configure(state="disabled")
            self.menu_ressource.set("Eau")
        elif m == "Extracteur de pétrole":
            self.seg_tier.configure(state="disabled")
            self.seg_purete.configure(state="normal")
            self.menu_ressource.set("Pétrole brut")
        else:
            # Extracteur moddé personnalisé
            self.seg_tier.configure(state="disabled")
            self.seg_purete.configure(state="normal")
        self.seg_somers.set("0")
        self.maj_resume_carte()
        if declencher:
            declencher_calcul()
    def exporter_dict(self):
        return {
            "machine": self.menu_machine.get(), "tier": self.seg_tier.get(),
            "purete": self.seg_purete.get(), "ressource": self.menu_ressource.get(),
            "qte": self.entree_qte.get().strip(), "cadence": self.entree_cadence.get().strip().replace("%", ""),
            "somers": "0", "nom": self.ent_nom.get().strip()
        }
    def supprimer(self):
        if self in cartes_foreuses:
            cartes_foreuses.remove(self)
        self.destroy()
        organiser_cartes_grille(cartes_foreuses, scroll_foreuses)
        declencher_calcul()
class CarteParcEnergetique(ctk.CTkFrame):
    """

    Parc Énergétique Standard avec choix du nombre de Raffineries / Extracteurs / Pompes

    dans chaque étape lorsque l'on est en mode 'Parc Fixe (Existant)'.

    """
    def __init__(self, master, numero, init_data=None):
        super().__init__(master, fg_color=THEME["bg_card"], border_color=THEME["tab_sel"], border_width=2, corner_radius=12)
        self.numero = numero
        self.cadences_etapes = {}
        self.qtes_etapes = {}  # eid -> str ("0" = Auto, sinon nombre manuel de raffineries/extracteurs)
        self.puretes_etapes = {}
        self.widgets_etapes = []
        paliers = generer_paliers_cadence()
        row1 = ctk.CTkFrame(self, fg_color=THEME["bg_card"])
        row1.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(row1, text=f"⚡ PARC ÉNERGÉTIQUE #{numero:02d}", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), fg_color=THEME["tab_sel"], text_color="#FFFFFF", corner_radius=6, padx=10, pady=4).pack(side="left", padx=(0, 10))
        self.menu_filiere = ctk.CTkOptionMenu(row1, values=list(FILIERES_ENERGIE.keys()), width=340, fg_color=THEME["bg_card_alt"], button_color=THEME["tab_sel"], text_color=THEME["text_main"], font=ctk.CTkFont(size=12, weight="bold"), command=self.on_filiere_change)
        self.menu_filiere.pack(side="left", padx=(0, 10))
        self.var_actif = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(row1, text="Connecté au Réseau", variable=self.var_actif, progress_color=THEME["status_ok"], text_color=THEME["text_main"], font=ctk.CTkFont(size=12, weight="bold"), command=declencher_calcul).pack(side="left", padx=10)
        ctk.CTkButton(row1, text="✕ SUPPRIMER PARC", width=130, height=28, corner_radius=8, fg_color="#991B1B", hover_color="#7F1D1D", text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), command=self.supprimer).pack(side="right")
        row2 = ctk.CTkFrame(self, fg_color=THEME["bg_card_alt"], corner_radius=8)
        row2.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row2, text="Mode :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(10, 6), pady=8)
        self.seg_mode = ctk.CTkSegmentedButton(row2, values=["Parc Fixe (Existant)", "Auto-Compensation Déficit"], fg_color=THEME["bg_panel"], selected_color=THEME["tab_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=self.on_mode_change)
        self.seg_mode.set("Parc Fixe (Existant)")
        self.seg_mode.pack(side="left", padx=(0, 12), pady=8)
        self.lbl_nb_fixe = ctk.CTkLabel(row2, text="Nb Centrales :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"])
        self.entree_nb_fixe = ctk.CTkEntry(row2, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=13, weight="bold"))
        self.entree_nb_fixe.insert(0, "4")
        self.entree_nb_fixe.bind("<KeyRelease>", lambda _: planifier_calcul())
        self.lbl_portee = ctk.CTkLabel(row2, text="Ressources / déficit :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"])
        self.seg_portee = ctk.CTkSegmentedButton(row2, values=["Usine Active", "Réseau Global"], fg_color=THEME["bg_panel"], selected_color=THEME["seg_sel"], text_color="#FFFFFF", command=lambda _: declencher_calcul())
        self.seg_portee.set("Réseau Global")
        ajouter_bouton_aide(row2, "La chaîne utilise d’abord les ressources déjà disponibles. « Usine Active » regarde l’usine à laquelle ce parc appartient ; « Réseau Global » regarde le surplus de toutes les usines. En mode automatique, ce choix détermine aussi où chercher le déficit électrique.")
        self.var_boucle = ctk.BooleanVar(value=True)
        self.chk_boucle = ctk.CTkCheckBox(row2, text="🔄 Auto-alimenter la cascade", variable=self.var_boucle, text_color=THEME["text_main"], font=ctk.CTkFont(size=12), command=declencher_calcul)
        self.chk_boucle.pack(side="right", padx=12, pady=8)
        row3 = ctk.CTkFrame(self, fg_color=THEME["bg_card_alt"], corner_radius=8)
        row3.pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(row3, text="Cadence Centrales (%) :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(10, 6), pady=8)
        self.seg_surc_gen = ctk.CTkSegmentedButton(row3, values=paliers, fg_color=THEME["bg_panel"], selected_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), command=self.on_quick_gen_surc)
        self.seg_surc_gen.set("100%")
        self.seg_surc_gen.pack(side="left", padx=4, pady=8)
        self.entree_cadence_gen = ctk.CTkEntry(row3, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
        self.entree_cadence_gen.pack(side="left", padx=6, pady=8)
        self.entree_cadence_gen.insert(0, "100")
        self.entree_cadence_gen.bind("<KeyRelease>", self.on_manual_gen_surc)
        self.badge_bilan_parc = ctk.CTkLabel(row3, text="0x Centrale ➔ +0.0 MW", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), fg_color=THEME["status_ok"], text_color="#000000", corner_radius=6, padx=10, pady=4)
        self.badge_bilan_parc.pack(side="right", padx=10)
        self.frame_etapes = ctk.CTkFrame(self, fg_color=THEME["bg_card"])
        self.frame_etapes.pack(fill="x", padx=12, pady=(4, 10))
        if init_data:
            if init_data.get("filiere") in FILIERES_ENERGIE:
                self.menu_filiere.set(init_data["filiere"])
            self.seg_mode.set(init_data.get("mode", "Parc Fixe (Existant)"))
            self.seg_portee.set(init_data.get("portee_auto", "Réseau Global"))
            self.entree_nb_fixe.delete(0, "end")
            self.entree_nb_fixe.insert(0, str(init_data.get("nb_fixe", "4")))
            self.entree_cadence_gen.delete(0, "end")
            self.entree_cadence_gen.insert(0, str(init_data.get("cadence_gen", "100")))
            c_txt = f"{init_data.get('cadence_gen', '100')}%"
            if c_txt in paliers:
                self.seg_surc_gen.set(c_txt)
            self.var_boucle.set(init_data.get("boucle_auto", True))
            self.var_actif.set(init_data.get("actif", True))
            self.cadences_etapes = dict(init_data.get("cadences_etapes", {}))
            self.qtes_etapes = dict(init_data.get("qtes_etapes", {}))
            self.puretes_etapes = dict(init_data.get("puretes_etapes", {}))
        self.on_mode_change(declencher=False)
        self.reconstruire_etapes_ui(declencher=False)
    def on_quick_gen_surc(self, val):
        self.entree_cadence_gen.delete(0, "end")
        self.entree_cadence_gen.insert(0, val.replace("%", ""))
        declencher_calcul()
    def on_manual_gen_surc(self, _=None):
        txt = self.entree_cadence_gen.get().strip().replace("%", "")
        if f"{txt}%" in generer_paliers_cadence():
            self.seg_surc_gen.set(f"{txt}%")
        planifier_calcul()
    def on_mode_change(self, _=None, declencher=True):
        mode = self.seg_mode.get()
        if mode == "Parc Fixe (Existant)":
            self.lbl_nb_fixe.pack(side="left", padx=(6, 4), pady=8)
            self.entree_nb_fixe.pack(side="left", padx=(0, 10), pady=8)
            self.lbl_portee.configure(text="Ressources disponibles :")
        else:
            self.lbl_nb_fixe.pack_forget()
            self.entree_nb_fixe.pack_forget()
            self.lbl_portee.configure(text="Ressources / déficit :")
        if not self.lbl_portee.winfo_manager():
            self.lbl_portee.pack(side="left", padx=(6, 4), pady=8)
        if not self.seg_portee.winfo_manager():
            self.seg_portee.pack(side="left", padx=(0, 10), pady=8)
        if declencher:
            declencher_calcul()
    def on_filiere_change(self, _=None):
        self.reconstruire_etapes_ui(declencher=True)
    def reconstruire_etapes_ui(self, declencher=True):
        for w in self.widgets_etapes:
            w["frame"].destroy()
        self.widgets_etapes.clear()
        paliers = generer_paliers_cadence()
        spec = FILIERES_ENERGIE[self.menu_filiere.get()]
        for idx, etape in enumerate(spec["etapes"], start=1):
            eid = etape["id"]
            cad_init = str(self.cadences_etapes.get(eid, "100")).replace("%", "")
            qte_init = str(self.qtes_etapes.get(eid, "0")).strip()
            purete_init = self.puretes_etapes.get(eid, "Normal (1.0x)")
            self.cadences_etapes[eid] = cad_init
            self.qtes_etapes[eid] = qte_init
            self.puretes_etapes[eid] = purete_init
            f_step = ctk.CTkFrame(self.frame_etapes, fg_color=THEME["bg_card_alt"], border_color=THEME["border"], border_width=1, corner_radius=8)
            f_step.pack(fill="x", pady=3)
            r_top = ctk.CTkFrame(f_step, fg_color=THEME["bg_card_alt"])
            r_top.pack(fill="x", padx=10, pady=(6, 2))
            ctk.CTkLabel(r_top, text=f"Étape {idx} : {etape['nom']} ({etape['recette']})", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left")
            # Choix manuel du nombre de Raffineries / Extracteurs / Pompes
            ctk.CTkLabel(r_top, text="Qté Machines (0=Auto) :", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_muted"]).pack(side="left", padx=(16, 4))
            ent_qte_m = ctk.CTkEntry(r_top, width=52, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
            ent_qte_m.insert(0, qte_init)
            ent_qte_m.pack(side="left", padx=2)
            def make_qte_cb(step_id, e_q):
                def _cb(_=None):
                    self.qtes_etapes[step_id] = e_q.get().strip()
                    planifier_calcul()
                return _cb
            ent_qte_m.bind("<KeyRelease>", make_qte_cb(eid, ent_qte_m))
            lbl_res_step = ctk.CTkLabel(r_top, text="0x Machine", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=THEME["status_ok"])
            lbl_res_step.pack(side="right")
            purity_control = None
            if "Foreuse Mk." in etape["machine"] or "Extracteur de pétrole" in etape["machine"]:
                ctk.CTkLabel(r_top, text="Pureté :", text_color=THEME["text_muted"]).pack(side="left", padx=(8, 3))
                purity_control = ctk.CTkOptionMenu(
                    r_top, values=list(MULTIPLICATEUR_PURETE), width=130,
                    fg_color=THEME["bg_card"], button_color=THEME["tab_sel"],
                    text_color=THEME["text_main"],
                    command=lambda value, step_id=eid: (
                        self.puretes_etapes.update({step_id: value}),
                        planifier_calcul()
                    )
                )
                purity_control.set(purete_init if purete_init in MULTIPLICATEUR_PURETE else "Normal (1.0x)")
                purity_control.pack(side="left", padx=2)
            r_bot = ctk.CTkFrame(f_step, fg_color=THEME["bg_card_alt"])
            r_bot.pack(fill="x", padx=10, pady=(2, 6))
            ctk.CTkLabel(r_bot, text="Surcadençage :", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"]).pack(side="left", padx=(0, 6))
            ent_step = ctk.CTkEntry(r_bot, width=55, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=11, weight="bold"))
            ent_step.insert(0, cad_init)
            def make_quick_cb(step_id, entry_w):
                def _cb(val):
                    v_clean = val.replace("%", "")
                    self.cadences_etapes[step_id] = v_clean
                    entry_w.delete(0, "end")
                    entry_w.insert(0, v_clean)
                    declencher_calcul()
                return _cb
            seg_step = ctk.CTkSegmentedButton(r_bot, values=paliers, fg_color=THEME["bg_panel"], selected_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(family="Consolas", size=10, weight="bold"), command=make_quick_cb(eid, ent_step))
            if f"{cad_init}%" in paliers:
                seg_step.set(f"{cad_init}%")
            seg_step.pack(side="left", padx=4)
            def make_manual_cb(step_id, seg_w, entry_w):
                def _cb(_=None):
                    v_clean = entry_w.get().strip().replace("%", "")
                    self.cadences_etapes[step_id] = v_clean
                    if f"{v_clean}%" in generer_paliers_cadence():
                        seg_w.set(f"{v_clean}%")
                    planifier_calcul()
                return _cb
            ent_step.bind("<KeyRelease>", make_manual_cb(eid, seg_step, ent_step))
            ent_step.pack(side="left", padx=6)
            lbl_flux_step = ctk.CTkLabel(r_bot, text="", font=ctk.CTkFont(family="Consolas", size=11), text_color=THEME["text_muted"])
            lbl_flux_step.pack(side="right", padx=6)
            self.widgets_etapes.append({
                "frame": f_step, "etape": etape, "lbl_res": lbl_res_step,
                "lbl_flux": lbl_flux_step, "seg": seg_step, "entry": ent_step, "entry_qte": ent_qte_m,
                "purete": purity_control
            })
        if declencher:
            declencher_calcul()
    def exporter_dict(self):
        return {
            "filiere": self.menu_filiere.get(), "mode": self.seg_mode.get(),
            "portee_auto": self.seg_portee.get(), "nb_fixe": self.entree_nb_fixe.get().strip(),
            "cadence_gen": self.entree_cadence_gen.get().strip().replace("%", ""),
            "boucle_auto": self.var_boucle.get(), "actif": self.var_actif.get(),
            "cadences_etapes": dict(self.cadences_etapes), "qtes_etapes": dict(self.qtes_etapes),
            "puretes_etapes": dict(self.puretes_etapes)
        }
    def supprimer(self):
        if self in cartes_parcs_energie:
            cartes_parcs_energie.remove(self)
        self.destroy()
        declencher_calcul()
class CarteRefinedPower(ctk.CTkFrame):
    """

    Chaîne Modulaire REFINED POWER :

    Chaudière (Combustible + Eau ➔ Vapeur m³/min) ➔ Turbine (Vapeur ➔ Rotation RPM) ➔ Alternateur (RPM ➔ MW Électriques)

    """
    def __init__(self, master, numero, init_data=None):
        super().__init__(master, fg_color=THEME["bg_card"], border_color=THEME["accent_purple"], border_width=2, corner_radius=12)
        self.numero = numero
        r1 = ctk.CTkFrame(self, fg_color=THEME["bg_card"])
        r1.pack(fill="x", padx=12, pady=(10, 4))
        ctk.CTkLabel(r1, text=f"⚙️ REFINED POWER #{numero:02d} (VAPEUR ➔ RPM ➔ MW)", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), fg_color=THEME["accent_purple"], text_color="#FFFFFF", corner_radius=6, padx=10, pady=4).pack(side="left", padx=(0, 10))
        self.badge_mw = ctk.CTkLabel(r1, text="🌀 0 RPM  ➔  ⚡ +0.0 MW", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), fg_color=THEME["status_ok"], text_color="#000000", corner_radius=6, padx=10, pady=4)
        self.badge_mw.pack(side="left", padx=10)
        ctk.CTkButton(r1, text="✕ RETIRER CHAÎNE RP", width=140, height=28, corner_radius=8, fg_color="#991B1B", hover_color="#7F1D1D", text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), command=self.supprimer).pack(side="right")
        # Étape 1 : Chaudières (Production de Vapeur)
        f_boil = ctk.CTkFrame(self, fg_color=THEME["bg_card_alt"], corner_radius=8)
        f_boil.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(f_boil, text="1. Chaudière :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(10, 4), pady=8)
        self.menu_boiler = ctk.CTkOptionMenu(f_boil, values=get_machines_par_categorie("Refined Power : Chaudière (Vapeur)"), width=220, fg_color=THEME["bg_card"], button_color=THEME["tab_sel"], text_color=THEME["text_main"], command=self.on_boiler_select)
        self.menu_boiler.pack(side="left", padx=4)
        ctk.CTkLabel(f_boil, text="Qté :", text_color=THEME["text_main"]).pack(side="left", padx=(8, 2))
        self.ent_nb_boiler = ctk.CTkEntry(f_boil, width=50, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_nb_boiler.insert(0, "2")
        self.ent_nb_boiler.pack(side="left", padx=2)
        self.ent_nb_boiler.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkLabel(f_boil, text="Combustible :", text_color=THEME["text_main"]).pack(side="left", padx=(8, 2))
        self.menu_fuel = ctk.CTkComboBox(f_boil, values=["Charbon", "Carburant", "Turbocarburant", "Charbon compacté", "Barre de combustible à l'uranium"], width=155, fg_color=THEME["bg_card"], text_color=THEME["text_main"], command=lambda _: declencher_calcul())
        self.menu_fuel.set("Charbon")
        self.menu_fuel.pack(side="left", padx=2)
        ctk.CTkLabel(f_boil, text="Conso/min :", text_color=THEME["text_muted"]).pack(side="left", padx=(6, 2))
        self.ent_fuel_rate = ctk.CTkEntry(f_boil, width=50, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_fuel_rate.insert(0, "15")
        self.ent_fuel_rate.pack(side="left", padx=2)
        self.ent_fuel_rate.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkLabel(f_boil, text="Eau/min :", text_color=THEME["text_muted"]).pack(side="left", padx=(6, 2))
        self.ent_water_rate = ctk.CTkEntry(f_boil, width=50, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_water_rate.insert(0, "45")
        self.ent_water_rate.pack(side="left", padx=2)
        self.ent_water_rate.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkLabel(f_boil, text="Vapeur produite/u :", text_color=THEME["text_muted"]).pack(side="left", padx=(6, 2))
        self.ent_steam_out = ctk.CTkEntry(f_boil, width=55, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_steam_out.insert(0, "60")
        self.ent_steam_out.pack(side="left", padx=2)
        self.ent_steam_out.bind("<KeyRelease>", lambda _: planifier_calcul())
        # Étape 2 : Turbines (Vapeur -> RPM) + Étape 3 : Alternateurs (RPM -> MW)
        f_turb = ctk.CTkFrame(self, fg_color=THEME["bg_card_alt"], corner_radius=8)
        f_turb.pack(fill="x", padx=12, pady=3)
        ctk.CTkLabel(f_turb, text="2. Turbine :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(10, 4), pady=8)
        self.menu_turbine = ctk.CTkOptionMenu(f_turb, values=get_machines_par_categorie("Refined Power : Turbine (RPM)"), width=200, fg_color=THEME["bg_card"], button_color=THEME["seg_sel"], text_color=THEME["text_main"], command=self.on_turbine_select)
        self.menu_turbine.pack(side="left", padx=4)
        ctk.CTkLabel(f_turb, text="Qté :", text_color=THEME["text_main"]).pack(side="left", padx=(6, 2))
        self.ent_nb_turb = ctk.CTkEntry(f_turb, width=45, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_nb_turb.insert(0, "2")
        self.ent_nb_turb.pack(side="left", padx=2)
        self.ent_nb_turb.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkLabel(f_turb, text="Vapeur req/u :", text_color=THEME["text_muted"]).pack(side="left", padx=(6, 2))
        self.ent_steam_req = ctk.CTkEntry(f_turb, width=50, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_steam_req.insert(0, "60")
        self.ent_steam_req.pack(side="left", padx=2)
        self.ent_steam_req.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkLabel(f_turb, text="RPM/u :", text_color=THEME["text_muted"]).pack(side="left", padx=(6, 2))
        self.ent_rpm_unit = ctk.CTkEntry(f_turb, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_rpm_unit.insert(0, "1500")
        self.ent_rpm_unit.pack(side="left", padx=2)
        self.ent_rpm_unit.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkLabel(f_turb, text="3. Alternateur :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(12, 4))
        self.menu_gen = ctk.CTkOptionMenu(f_turb, values=get_machines_par_categorie("Refined Power : Alternateur (RPM ➔ MW)"), width=210, fg_color=THEME["bg_card"], button_color=THEME["accent_purple"], text_color=THEME["text_main"], command=self.on_gen_select)
        self.menu_gen.pack(side="left", padx=4)
        ctk.CTkLabel(f_turb, text="Qté :", text_color=THEME["text_main"]).pack(side="left", padx=(6, 2))
        self.ent_nb_gen = ctk.CTkEntry(f_turb, width=45, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_nb_gen.insert(0, "2")
        self.ent_nb_gen.pack(side="left", padx=2)
        self.ent_nb_gen.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkLabel(f_turb, text="Ratio MW/RPM :", text_color=THEME["text_muted"]).pack(side="left", padx=(6, 2))
        self.ent_ratio_mw = ctk.CTkEntry(f_turb, width=55, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_ratio_mw.insert(0, "0.10")
        self.ent_ratio_mw.pack(side="left", padx=2)
        self.ent_ratio_mw.bind("<KeyRelease>", lambda _: planifier_calcul())
        self.lbl_details = ctk.CTkLabel(self, text="💨 Vapeur : 0.0 / 0.0 m³/min  │  ⚙️ Rotation : 0 RPM  │  ⚡ Net : +0.0 MW", font=ctk.CTkFont(family="Consolas", size=12), text_color=THEME["text_muted"], anchor="w")
        self.lbl_details.pack(fill="x", padx=14, pady=(2, 8))
        if init_data:
            self.menu_boiler.set(init_data.get("boiler", self.menu_boiler.get()))
            self.ent_nb_boiler.delete(0, "end"); self.ent_nb_boiler.insert(0, str(init_data.get("nb_boiler", "2")))
            self.menu_fuel.set(init_data.get("fuel", "Charbon"))
            self.ent_fuel_rate.delete(0, "end"); self.ent_fuel_rate.insert(0, str(init_data.get("fuel_rate", "15")))
            self.ent_water_rate.delete(0, "end"); self.ent_water_rate.insert(0, str(init_data.get("water_rate", "45")))
            self.ent_steam_out.delete(0, "end"); self.ent_steam_out.insert(0, str(init_data.get("steam_out", "60")))
            self.menu_turbine.set(init_data.get("turbine", self.menu_turbine.get()))
            self.ent_nb_turb.delete(0, "end"); self.ent_nb_turb.insert(0, str(init_data.get("nb_turb", "2")))
            self.ent_steam_req.delete(0, "end"); self.ent_steam_req.insert(0, str(init_data.get("steam_req", "60")))
            self.ent_rpm_unit.delete(0, "end"); self.ent_rpm_unit.insert(0, str(init_data.get("rpm_unit", "1500")))
            self.menu_gen.set(init_data.get("gen", self.menu_gen.get()))
            self.ent_nb_gen.delete(0, "end"); self.ent_nb_gen.insert(0, str(init_data.get("nb_gen", "2")))
            self.ent_ratio_mw.delete(0, "end"); self.ent_ratio_mw.insert(0, str(init_data.get("ratio_mw", "0.10")))
    def on_boiler_select(self, nom_b):
        sp = get_machine_specs(nom_b)
        presets_b = {
            "RP Chaudière Mk.1 (Firebox)": ("Charbon", "15", "45", "60"),
            "RP Chaudière Mk.2 (Haute Pression)": ("Charbon", "30", "120", "180"),
            "RP Réacteur Vapeur Nucléaire": ("Barre de combustible à l'uranium", "0.2", "240", "600")
        }
        if nom_b in presets_b:
            fl, fr, wr, st = presets_b[nom_b]
            self.menu_fuel.set(fl)
            self.ent_fuel_rate.delete(0, "end"); self.ent_fuel_rate.insert(0, fr)
            self.ent_water_rate.delete(0, "end"); self.ent_water_rate.insert(0, wr)
            self.ent_steam_out.delete(0, "end"); self.ent_steam_out.insert(0, st)
        elif sp.get("valeur_spec", 0) > 0:
            self.ent_steam_out.delete(0, "end")
            self.ent_steam_out.insert(0, str(sp["valeur_spec"]))
        declencher_calcul()
    def on_turbine_select(self, nom_t):
        sp = get_machine_specs(nom_t)
        if sp.get("valeur_spec", 0) > 0:
            self.ent_rpm_unit.delete(0, "end")
            self.ent_rpm_unit.insert(0, str(sp["valeur_spec"]))
        declencher_calcul()
    def on_gen_select(self, nom_g):
        sp = get_machine_specs(nom_g)
        if sp.get("valeur_spec", 0) > 0:
            self.ent_ratio_mw.delete(0, "end")
            self.ent_ratio_mw.insert(0, str(sp["valeur_spec"]))
        declencher_calcul()
    def exporter_dict(self):
        return {
            "boiler": self.menu_boiler.get(), "nb_boiler": self.ent_nb_boiler.get().strip(),
            "fuel": self.menu_fuel.get(), "fuel_rate": self.ent_fuel_rate.get().strip(),
            "water_rate": self.ent_water_rate.get().strip(), "steam_out": self.ent_steam_out.get().strip(),
            "turbine": self.menu_turbine.get(), "nb_turb": self.ent_nb_turb.get().strip(),
            "steam_req": self.ent_steam_req.get().strip(), "rpm_unit": self.ent_rpm_unit.get().strip(),
            "gen": self.menu_gen.get(), "nb_gen": self.ent_nb_gen.get().strip(),
            "ratio_mw": self.ent_ratio_mw.get().strip()
        }
    def supprimer(self):
        if self in cartes_refined_power:
            cartes_refined_power.remove(self)
        self.destroy()
        declencher_calcul()
DS_TYPE_BAIE = "Baie de Disques (configuration personnalisée)"
DS_SLOTS_BAIE = 22
DS_SERVEURS = {
    "Serveur 1U (Item)": {"famille": "Item", "max": 22, "slots": 4, "rack_slots": 1},
    "Serveur 1U (Fluide)": {"famille": "Fluide", "max": 22, "slots": 4, "rack_slots": 1},
    "Serveur 2U (Item)": {"famille": "Item", "max": 11, "slots": 12, "rack_slots": 2},
    "Serveur 2U (Fluide)": {"famille": "Fluide", "max": 11, "slots": 12, "rack_slots": 2},
    "Serveur 2U (Gaz)": {"famille": "Gaz", "max": 11, "slots": 12, "rack_slots": 2},
    "Serveur de Craft": {"famille": None, "max": 22, "slots": 0, "rack_slots": 1}
}
DS_ALIAS_SERVEURS = {
    "Serveur (Item)": "Serveur 2U (Item)",
    "Serveur (Fluide)": "Serveur 2U (Fluide)",
    "Serveur (Gaz)": "Serveur 2U (Gaz)"
}
DS_DISQUES = {
    "Item": [
        "DS DRIVE 256 (Item)", "DS DRIVE 512 (Item)", "DS DRIVE 1K (Item)",
        "DS DRIVE 2K (Item)", "DS DRIVE 4K (Item)", "DS DRIVE 8K (Item)",
        "DS DRIVE 16K (Item)", "DS DRIVE 32K (Item)", "DS DRIVE 64K (Item)"
    ],
    "Fluide": [
        "DS DRIVE 10 m³ (Fluide)", "DS DRIVE 20 m³ (Fluide)",
        "DS DRIVE 40 m³ (Fluide)", "DS DRIVE 60 m³ (Fluide)",
        "DS DRIVE 120 m³ (Fluide)", "DS DRIVE 240 m³ (Fluide)"
    ],
    "Gaz": [
        "DS DRIVE 40 m³ (Gaz)", "DS DRIVE 60 m³ (Gaz)",
        "DS DRIVE 120 m³ (Gaz)", "DS DRIVE 240 m³ (Gaz)"
    ]
}
DS_DEFAUTS_DISQUES = {
    "DS DRIVE 256 (Item)": ("4", "256"),
    "DS DRIVE 512 (Item)": ("4", "512"),
    "DS DRIVE 1K (Item)": ("4", "1000"),
    "DS DRIVE 2K (Item)": ("4", "2000"),
    "DS DRIVE 4K (Item)": ("8", "4000"),
    "DS DRIVE 8K (Item)": ("8", "8000"),
    "DS DRIVE 16K (Item)": ("8", "16000"),
    "DS DRIVE 32K (Item)": ("8", "32000"),
    "DS DRIVE 64K (Item)": ("8", "64000"),
    "DS DRIVE 10 m³ (Fluide)": ("4", "10000"),
    "DS DRIVE 20 m³ (Fluide)": ("8", "20000"),
    "DS DRIVE 40 m³ (Fluide)": ("8", "40000"),
    "DS DRIVE 60 m³ (Fluide)": ("8", "60000"),
    "DS DRIVE 120 m³ (Fluide)": ("8", "120000"),
    "DS DRIVE 240 m³ (Fluide)": ("8", "240000"),
    "DS DRIVE 40 m³ (Gaz)": ("8", "40000"),
    "DS DRIVE 60 m³ (Gaz)": ("8", "60000"),
    "DS DRIVE 120 m³ (Gaz)": ("8", "120000"),
    "DS DRIVE 240 m³ (Gaz)": ("8", "240000")
}
def resumer_baie_ds(config):
    erreurs = []
    serveurs = config.get("serveurs", {})
    nb_serveurs = 0
    slots_baie = 0
    slots_famille = {"Item": 0, "Fluide": 0, "Gaz": 0}
    for nom, spec in DS_SERVEURS.items():
        try:
            ancien_nom = next((alias for alias, nouveau in DS_ALIAS_SERVEURS.items() if nouveau == nom), None)
            raw_q = str(serveurs.get(nom, serveurs.get(ancien_nom, "0"))).strip()
            qte = int(raw_q) if raw_q != "" else 0
        except (TypeError, ValueError):
            erreurs.append(f"Nombre invalide pour {nom}.")
            continue
        if qte < 0 or qte > spec["max"]:
            erreurs.append(f"{nom} : entre 0 et {spec['max']} serveur(s).")
            continue
        nb_serveurs += qte
        slots_baie += qte * spec["rack_slots"]
        if spec["famille"]:
            slots_famille[spec["famille"]] += qte * spec["slots"]
    if slots_baie > DS_SLOTS_BAIE:
        erreurs.append(f"La baie utilise {slots_baie}/{DS_SLOTS_BAIE} slots de rack (dépassement de {slots_baie - DS_SLOTS_BAIE}).")
    disques_installes = {"Item": 0, "Fluide": 0, "Gaz": 0}
    capacite_octets = 0
    disque_par_famille = {nom: famille for famille, noms in DS_DISQUES.items() for nom in noms}
    for disque in config.get("disques", []):
        nom = disque.get("type")
        famille = disque_par_famille.get(nom)
        if famille is None:
            continue
        raw_dq = str(disque.get("qte", "0")).strip()
        try:
            qte = int(raw_dq) if raw_dq != "" else 0
        except (TypeError, ValueError):
            erreurs.append(f"Nombre de disques invalide pour {nom}.")
            continue
        if qte < 0:
            erreurs.append(f"Le nombre de disques ne peut pas être négatif ({nom}).")
        if qte <= 0:
            continue
        def_p, def_o = DS_DEFAUTS_DISQUES.get(nom, ("1", "256"))
        raw_p = str(disque.get("partitions_max", "")).strip() or def_p
        raw_o = str(disque.get("octets_par_disque", "")).strip() or def_o
        try:
            partitions = int(raw_p)
            octets = int(raw_o)
        except (TypeError, ValueError):
            erreurs.append(f"Renseignez des nombres valides (partitions/octets) pour {nom}.")
            continue
        if partitions <= 0 or octets <= 0:
            erreurs.append(f"{nom} doit avoir au moins 1 partition et 1 octet.")
            continue
        disques_installes[famille] += qte
        capacite_octets += qte * octets
    for famille, qte in disques_installes.items():
        if qte > slots_famille[famille]:
            erreurs.append(f"{famille} : {qte} disque(s) installé(s) pour {slots_famille[famille]} emplacement(s) disponible(s).")
    return capacite_octets, nb_serveurs, slots_baie, erreurs

def nombre_cases_serveur_visibles(spec, nombre_coche, slots_utilises, dernier_coche):
    slots_restants = max(DS_SLOTS_BAIE - slots_utilises, 0)
    choix_disponibles = nombre_coche + slots_restants // spec["rack_slots"]
    return min(spec["max"], max(dernier_coche, choix_disponibles))

def calculer_couts_construction(compteurs, recettes):
    totaux = {}
    sans_recette = []
    for nom_batiment, nombre in compteurs.items():
        if nombre <= 0:
            continue
        recette = recettes.get(nom_batiment, {})
        if not isinstance(recette, dict) or not recette:
            sans_recette.append((nom_batiment, nombre))
            continue
        for nom_ressource, cout_unitaire in recette.items():
            try:
                cout_total = float(cout_unitaire) * nombre
            except (TypeError, ValueError):
                continue
            if cout_total > 0:
                totaux[nom_ressource] = totaux.get(nom_ressource, 0.0) + cout_total
    return totaux, sans_recette

class CarteEquipementDigitalStorage(ctk.CTkFrame):
    """Équipement d'infrastructure du mod Digital Storage."""
    def __init__(self, master, init_data=None):
        super().__init__(master, fg_color=THEME["bg_card_alt"], border_color=THEME["border"], border_width=1, corner_radius=8)
        self._job_baie = None
        self._familles_affiches = None
        presets_ds = [
            "Contrôleur Réseau Central",
            DS_TYPE_BAIE,
            "Baie de Disques + Disques 16k",
            "Baie de Disques + Disques 64k",
            "Bus d'Import / Export Haut Débit",
            "Terminal d'Accès Sans-Fil",
            "Routeur Cloud Inter-Usines",
            "Network Power Adapter"
        ]
        self.frame_entete = ctk.CTkFrame(self, fg_color=THEME["bg_card_alt"])
        self.frame_entete.pack(fill="x")
        ctk.CTkLabel(self.frame_entete, text="🖥️ Équipement :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(10, 4), pady=8)
        self.combo_type = ctk.CTkComboBox(self.frame_entete, values=presets_ds, width=260, fg_color=THEME["bg_card"], text_color=THEME["text_main"], command=self.on_preset)
        self.combo_type.pack(side="left", padx=4)
        self.combo_type.set("Contrôleur Réseau Central")
        ctk.CTkLabel(self.frame_entete, text="Qté (baies/équipements) :", text_color=THEME["text_main"]).pack(side="left", padx=(8, 2))
        self.ent_qte = ctk.CTkEntry(self.frame_entete, width=50, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_qte.insert(0, "1")
        self.ent_qte.pack(side="left", padx=2)
        self.ent_qte.bind("<KeyRelease>", lambda _: planifier_calcul())
        ajouter_bouton_aide(self.frame_entete, "La quantité indique combien d'équipements tu as. Le Network Power Adapter consomme 1000 MW par unité : écris ici combien tu en as pour compter cette énergie.")
        ctk.CTkLabel(self.frame_entete, text="Conso/u (MW) :", text_color=THEME["text_muted"]).pack(side="left", padx=(8, 2))
        self.ent_mw = ctk.CTkEntry(self.frame_entete, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_mw.insert(0, "50.0")
        self.ent_mw.pack(side="left", padx=2)
        self.ent_mw.bind("<KeyRelease>", lambda _: planifier_calcul())
        self.lbl_cap = ctk.CTkLabel(self.frame_entete, text="Capacité Items/u :", text_color=THEME["text_muted"])
        self.lbl_cap.pack(side="left", padx=(8, 2))
        self.ent_cap = ctk.CTkEntry(self.frame_entete, width=90, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_cap.insert(0, "0")
        self.ent_cap.pack(side="left", padx=2)
        self.ent_cap.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkLabel(self.frame_entete, text="Bande passante/u (/min) :", text_color=THEME["text_muted"]).pack(side="left", padx=(8, 2))
        self.ent_bw = ctk.CTkEntry(self.frame_entete, width=70, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        self.ent_bw.insert(0, "600")
        self.ent_bw.pack(side="left", padx=2)
        self.ent_bw.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkButton(self.frame_entete, text="✕", width=32, height=26, corner_radius=6, fg_color="#991B1B", text_color="#FFFFFF", command=self.supprimer).pack(side="right", padx=8)
        self.frame_baie = ctk.CTkFrame(self, fg_color=THEME["bg_card_alt"])
        row_serveurs_aide = ctk.CTkFrame(self.frame_baie, fg_color=THEME["bg_card_alt"])
        row_serveurs_aide.pack(fill="x", padx=6, pady=(4, 2))
        ctk.CTkLabel(row_serveurs_aide, text=f"Choisis le nombre de serveurs (la baie a {DS_SLOTS_BAIE} cases ; un serveur 2U prend deux cases) :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(0, 4))
        ajouter_bouton_aide(row_serveurs_aide, "Clique sur le numéro voulu : ce numéro et les précédents seront cochés. Exemple : cliquer sur 3 choisit 3 serveurs. Les numéros possibles diminuent quand les autres serveurs utilisent des cases.")
        self.frame_serveurs = ctk.CTkFrame(self.frame_baie, fg_color=THEME["bg_card_alt"])
        self.frame_serveurs.pack(fill="x", padx=4)
        self.ent_serveurs = {}
        self.serveur_vars = {}
        self.serveur_checks = {}
        self.lbl_serveurs = {}
        for index, (nom, spec) in enumerate(DS_SERVEURS.items()):
            ligne = ctk.CTkFrame(self.frame_serveurs, fg_color=THEME["bg_card_alt"])
            ligne.grid(row=index, column=0, sticky="w")
            self.lbl_serveurs[nom] = ctk.CTkLabel(ligne, text=f"{nom} : 0", width=190, anchor="w", text_color=THEME["text_muted"])
            self.lbl_serveurs[nom].pack(side="left", padx=(4, 2), pady=3)
            cases = ctk.CTkFrame(ligne, fg_color=THEME["bg_card_alt"])
            cases.pack(side="left")
            ent = ctk.CTkEntry(self.frame_serveurs, width=1)
            ent.insert(0, "0")
            self.ent_serveurs[nom] = ent
            self.serveur_vars[nom] = []
            self.serveur_checks[nom] = []
            for idx_serveur in range(spec["max"]):
                var = ctk.BooleanVar(value=False)
                case = ctk.CTkCheckBox(
                    cases, text=str(idx_serveur + 1), variable=var, width=27,
                    checkbox_width=15, checkbox_height=15, border_width=2,
                    fg_color=THEME["tab_sel"], hover_color=THEME["seg_sel"],
                    text_color=THEME["text_main"],
                    command=lambda nom=nom, idx=idx_serveur: self.actualiser_selection_serveurs(nom, idx)
                )
                case.grid(row=0, column=idx_serveur, padx=1, pady=2)
                self.serveur_vars[nom].append(var)
                self.serveur_checks[nom].append(case)
        self.frame_disques = ctk.CTkFrame(self.frame_baie, fg_color=THEME["bg_card_alt"])
        self.frame_disques.pack(fill="x", padx=4, pady=(4, 0))
        self.frame_disques.grid_columnconfigure(0, weight=1)
        self.frames_famille = {}
        self.champs_disques = {}
        for idx_fam, (famille, noms) in enumerate(DS_DISQUES.items()):
            cadre = ctk.CTkFrame(self.frame_disques, fg_color=THEME["bg_card"], corner_radius=8)
            cadre.grid(row=idx_fam, column=0, sticky="ew", padx=4, pady=4)
            cadre.grid_columnconfigure(0, weight=1)
            self.frames_famille[famille] = cadre
            ctk.CTkLabel(cadre, text=f"Disques {famille} — quantité installée, partitions max et octets/items par disque", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_main"]).grid(row=0, column=0, columnspan=4, padx=6, pady=(4, 2), sticky="w")
            for colonne, titre in enumerate(["Modèle", "Nombre installé", "Partitions max./disque", "Octets totaux/disque"]):
                ctk.CTkLabel(cadre, text=titre, text_color=THEME["text_muted"]).grid(row=1, column=colonne, padx=4, pady=2, sticky="w")
            for ligne, nom_disque in enumerate(noms, start=2):
                ctk.CTkLabel(cadre, text=nom_disque, text_color=THEME["text_main"]).grid(row=ligne, column=0, padx=6, pady=2, sticky="w")
                champs = {}
                def_part, def_oct = DS_DEFAUTS_DISQUES.get(nom_disque, ("1", "256"))
                for colonne, cle, largeur, val_def in [(1, "qte", 55, "0"), (2, "partitions_max", 75, def_part), (3, "octets_par_disque", 110, def_oct)]:
                    ent = ctk.CTkEntry(cadre, width=largeur, justify="center", fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"])
                    ent.insert(0, val_def)
                    ent.grid(row=ligne, column=colonne, padx=4, pady=2, sticky="w")
                    ent.bind("<KeyRelease>", lambda _, self=self: self.planifier_maj_baie())
                    champs[cle] = ent
                self.champs_disques[nom_disque] = champs
        self.lbl_resume_baie = ctk.CTkLabel(self.frame_baie, text="", font=ctk.CTkFont(size=11), text_color=THEME["text_muted"])
        self.lbl_resume_baie.pack(anchor="w", padx=8, pady=(4, 8))
        if init_data:
            self.combo_type.set(init_data.get("type", "Contrôleur Réseau Central"))
            self.ent_qte.delete(0, "end"); self.ent_qte.insert(0, str(init_data.get("qte", "1")))
            self.ent_mw.delete(0, "end"); self.ent_mw.insert(0, str(init_data.get("mw_unit", "50.0")))
            self.ent_cap.delete(0, "end"); self.ent_cap.insert(0, str(init_data.get("capacite_items", "0")))
            self.ent_bw.delete(0, "end"); self.ent_bw.insert(0, str(init_data.get("bande_passante", "600")))
            for nom, qte in init_data.get("serveurs", {}).items():
                nouveau_nom = DS_ALIAS_SERVEURS.get(nom, nom)
                if nouveau_nom in self.ent_serveurs:
                    self.ent_serveurs[nouveau_nom].delete(0, "end")
                    self.ent_serveurs[nouveau_nom].insert(0, str(qte))
                    try:
                        nb_coche = min(max(int(qte), 0), len(self.serveur_vars[nouveau_nom]))
                    except (TypeError, ValueError):
                        nb_coche = 0
                    for var in self.serveur_vars[nouveau_nom][:nb_coche]:
                        var.set(True)
            donnees_disques = {d.get("type"): d for d in init_data.get("disques", [])}
            for nom, champs in self.champs_disques.items():
                donnees = donnees_disques.get(nom, {})
                def_part, def_oct = DS_DEFAUTS_DISQUES.get(nom, ("1", "256"))
                for cle, def_v in (("qte", "0"), ("partitions_max", def_part), ("octets_par_disque", def_oct)):
                    valeur = str(donnees.get(cle, "")).strip() or def_v
                    champs[cle].delete(0, "end")
                    champs[cle].insert(0, valeur)
        self.actualiser_selection_serveurs(synchroniser=False)
        self.actualiser_config_baie(planifier=False)
    def actualiser_selection_serveurs(self, nom_serveur=None, index_case=None, synchroniser=True):
        if nom_serveur is not None and index_case is not None:
            variables = self.serveur_vars[nom_serveur]
            if variables[index_case].get():
                for var in variables[:index_case]:
                    var.set(True)
            else:
                for var in variables[index_case:]:
                    var.set(False)
        compteurs = {
            nom: sum(1 for var in variables if var.get())
            for nom, variables in self.serveur_vars.items()
        }
        slots_utilises = sum(
            compteurs[nom] * spec["rack_slots"]
            for nom, spec in DS_SERVEURS.items()
        )
        for nom, spec in DS_SERVEURS.items():
            if synchroniser:
                ent = self.ent_serveurs[nom]
                ent.delete(0, "end")
                ent.insert(0, str(compteurs[nom]))
            self.lbl_serveurs[nom].configure(text=f"{nom} : {compteurs[nom]}")
            dernier_coche = max(
                (idx + 1 for idx, var in enumerate(self.serveur_vars[nom]) if var.get()),
                default=0
            )
            qte_visible = nombre_cases_serveur_visibles(spec, compteurs[nom], slots_utilises, dernier_coche)
            for idx, case in enumerate(self.serveur_checks[nom]):
                if idx < qte_visible:
                    case.grid()
                else:
                    case.grid_remove()
        if synchroniser:
            self.planifier_maj_baie()
    def planifier_maj_baie(self):
        if self._job_baie is not None:
            try:
                app.after_cancel(self._job_baie)
            except Exception:
                pass
        self._job_baie = app.after(450, lambda: self.actualiser_config_baie(planifier=True))
    def actualiser_config_baie(self, planifier=True):
        self._job_baie = None
        est_baie = self.combo_type.get() == DS_TYPE_BAIE
        if est_baie:
            if not self.frame_baie.winfo_manager():
                self.frame_baie.pack(fill="x", padx=8, pady=(0, 6))
            self.lbl_cap.configure(text="Capacité Items/baie :")
            capacite, _, slots_baie, erreurs = resumer_baie_ds({
                "serveurs": {nom: ent.get().strip() for nom, ent in self.ent_serveurs.items()},
                "disques": [
                    {"type": nom, **{cle: ent.get().strip() for cle, ent in champs.items()}}
                    for nom, champs in self.champs_disques.items()
                ]
            })
            self.ent_cap.configure(state="normal")
            self.ent_cap.delete(0, "end"); self.ent_cap.insert(0, str(capacite if not erreurs else 0))
            self.ent_cap.configure(state="disabled")
            familles_actives = frozenset(
                spec["famille"] for nom, spec in DS_SERVEURS.items()
                if spec["famille"] and self.ent_serveurs[nom].get().strip().isdigit()
                and int(self.ent_serveurs[nom].get().strip()) > 0
            )
            if familles_actives != self._familles_affiches:
                self._familles_affiches = familles_actives
                for famille, cadre in self.frames_famille.items():
                    if famille in familles_actives:
                        cadre.grid()
                    else:
                        cadre.grid_remove()
            if erreurs:
                self.lbl_resume_baie.configure(text=f"⚠️ Rack : {slots_baie}/{DS_SLOTS_BAIE} slots. " + " ".join(erreurs), text_color=THEME["status_err"])
            else:
                self.lbl_resume_baie.configure(text=f"🗄️ Rack : {slots_baie}/{DS_SLOTS_BAIE} slots occupés ({DS_SLOTS_BAIE - slots_baie} libres)  │  💾 Capacité : {capacite:,} octets/items par baie.", text_color=THEME["status_ok"])
        else:
            if self.frame_baie.winfo_manager():
                self.frame_baie.pack_forget()
            self.lbl_cap.configure(text="Capacité Items/u :")
            self.ent_cap.configure(state="normal")
        if planifier:
            planifier_calcul()
    def on_preset(self, val):
        presets_vals = {
            "Contrôleur Réseau Central": ("50.0", "0", "600"),
            DS_TYPE_BAIE: ("35.0", "0", "1200"),
            "Baie de Disques + Disques 16k": ("25.0", "16000", "1200"),
            "Baie de Disques + Disques 64k": ("60.0", "64000", "2400"),
            "Bus d'Import / Export Haut Débit": ("10.0", "0", "780"),
            "Terminal d'Accès Sans-Fil": ("15.0", "0", "0"),
            "Routeur Cloud Inter-Usines": ("100.0", "0", "2400"),
            "Network Power Adapter": ("1000.0", "0", "0")
        }
        valeurs = presets_vals.get(val, ("25.0", "0", "1200"))
        for champ, valeur in zip((self.ent_mw, self.ent_cap, self.ent_bw), valeurs):
            champ.configure(state="normal")
            champ.delete(0, "end"); champ.insert(0, valeur)
        self.actualiser_config_baie(planifier=False)
        declencher_calcul()
    def exporter_dict(self):
        serveurs = {nom: ent.get().strip() for nom, ent in self.ent_serveurs.items()}
        disques = [
            {"type": nom, **{cle: ent.get().strip() for cle, ent in champs.items()}}
            for nom, champs in self.champs_disques.items()
        ]
        return {
            "type": self.combo_type.get(), "qte": self.ent_qte.get().strip(),
            "mw_unit": self.ent_mw.get().strip(), "capacite_items": self.ent_cap.get().strip(),
            "bande_passante": self.ent_bw.get().strip(),
            "serveurs": serveurs, "disques": disques
        }
    def maj_resume_baie(self, erreurs, capacite, slots_baie):
        if self.combo_type.get() != DS_TYPE_BAIE:
            return
        if erreurs:
            self.lbl_resume_baie.configure(text=f"⚠️ Rack : {slots_baie}/{DS_SLOTS_BAIE} slots. " + " ".join(erreurs), text_color=THEME["status_err"])
        else:
            self.lbl_resume_baie.configure(text=f"🗄️ Rack : {slots_baie}/{DS_SLOTS_BAIE} slots occupés ({DS_SLOTS_BAIE - slots_baie} libres)  │  💾 Capacité : {capacite:,} octets/items par baie.", text_color=THEME["status_ok"])
    def supprimer(self):
        if self in cartes_ds_equip:
            cartes_ds_equip.remove(self)
        self.destroy()
        declencher_calcul()
class CarteFluxDigitalStorage(ctk.CTkFrame):
    """Flux d'Import (Download dans l'usine) ou d'Export (Upload vers le Cloud Digital Storage)."""
    def __init__(self, master, init_data=None):
        super().__init__(master, fg_color=THEME["bg_card_alt"], border_color=THEME["border"], border_width=1, corner_radius=8)
        self.seg_sens = ctk.CTkSegmentedButton(self, values=["📤 Upload vers Cloud (Sort de l'usine)", "📥 Download depuis Cloud (Entre dans l'usine)"], fg_color=THEME["bg_panel"], selected_color=THEME["tab_sel"], text_color="#FFFFFF", command=lambda _: declencher_calcul())
        self.seg_sens.set("📤 Upload vers Cloud (Sort de l'usine)")
        self.seg_sens.pack(side="left", padx=10, pady=8)
        ctk.CTkLabel(self, text="Objet :", text_color=THEME["text_main"]).pack(side="left", padx=(8, 4))
        tous_items = sorted(list(set(liste_objets_produits + list(RESSOURCES_EXTRACTION_MAP.keys()))))
        self.combo_item = ctk.CTkComboBox(self, values=tous_items, width=220, fg_color=THEME["bg_card"], text_color=THEME["text_main"], command=lambda _: declencher_calcul())
        self.combo_item.pack(side="left", padx=4)
        self.combo_item.set("Lingot de fer" if "Lingot de fer" in tous_items else tous_items[0])
        ctk.CTkLabel(self, text="Débit (/min) :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
        self.ent_debit = ctk.CTkEntry(self, width=70, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
        self.ent_debit.insert(0, "60")
        self.ent_debit.pack(side="left", padx=4)
        self.ent_debit.bind("<KeyRelease>", lambda _: planifier_calcul())
        ctk.CTkButton(self, text="✕", width=32, height=26, corner_radius=6, fg_color="#991B1B", text_color="#FFFFFF", command=self.supprimer).pack(side="right", padx=8)
        if init_data:
            self.seg_sens.set(init_data.get("sens", "📤 Upload vers Cloud (Sort de l'usine)"))
            self.combo_item.set(init_data.get("item", "Lingot de fer"))
            self.ent_debit.delete(0, "end"); self.ent_debit.insert(0, str(init_data.get("debit", "60")))
    def exporter_dict(self):
        return {"sens": self.seg_sens.get(), "item": self.combo_item.get(), "debit": self.ent_debit.get().strip()}
    def supprimer(self):
        if self in cartes_ds_flux:
            cartes_ds_flux.remove(self)
        self.destroy()
        declencher_calcul()
# ==============================================================================
# 9. SYNCHRONISATION PAR DOSSIER D'USINE & MOTEUR DE CALCUL GLOBAL / LOCAL
# ==============================================================================
def synchroniser_usine_active():
    if verrou_chargement_ui or usine_active_nom not in usines_data:
        return
    u_curr = usines_data[usine_active_nom]
    u_curr["ateliers"] = [c.exporter_dict() for c in cartes_ateliers]
    u_curr["foreuses"] = [c.exporter_dict() for c in cartes_foreuses]
    u_curr["parcs_energie"] = [c.exporter_dict() for c in cartes_parcs_energie]
    u_curr["refined_power"] = [c.exporter_dict() for c in cartes_refined_power]
    u_curr["digital_storage"] = {
        "equipements": [c.exporter_dict() for c in cartes_ds_equip],
        "flux_cloud": [c.exporter_dict() for c in cartes_ds_flux]
    }
    sauvegarder_usine_dans_son_dossier(usine_active_nom, u_curr)
def simuler_parc_energetique(parc_cfg, cible_deficit_mw, flux_disponibles=None):
    if not parc_cfg.get("actif", True):
        return {"nb_gen": 0, "prod_brute_mw": 0.0, "mw_cascade": 0.0, "eclats": 0, "batiments": 0, "etapes_res": [], "flux_ext": {}}
    nom_fil = parc_cfg.get("filiere")
    if nom_fil not in FILIERES_ENERGIE:
        nom_fil = list(FILIERES_ENERGIE.keys())[0]
    spec = FILIERES_ENERGIE[nom_fil]
    try:
        cad_gen_pct = float(parc_cfg.get("cadence_gen", "100"))
    except ValueError:
        cad_gen_pct = 100.0
    if cad_gen_pct <= 0:
        return {"nb_gen": 0, "prod_brute_mw": 0.0, "mw_cascade": 0.0, "eclats": 0, "batiments": 0, "etapes_res": [], "flux_ext": {}}
    cad_gen = cad_gen_pct / 100.0
    mw_par_gen = spec["puissance_base"] * cad_gen
    eclats_par_gen = calculer_eclats_machine(cad_gen_pct)
    exp_surc = float(MODS_CONFIG.get("exposant_surcadencage", 1.6))
    mode = parc_cfg.get("mode", "Parc Fixe (Existant)")
    boucle_auto = parc_cfg.get("boucle_auto", True)
    qtes_manuelles = parc_cfg.get("qtes_etapes", {})
    flux_disponibles_initiaux = {
        item: max(float(qte), 0.0)
        for item, qte in (flux_disponibles or {}).items()
    }
    if mode == "Parc Fixe (Existant)":
        try:
            nb_gen_fixe = max(int(parc_cfg.get("nb_fixe", "0")), 0)
        except ValueError:
            nb_gen_fixe = 0
        nb_iter = 1
        cible_mw = nb_gen_fixe * mw_par_gen
    else:
        cible_mw = max(cible_deficit_mw, 0.0)
        nb_iter = 8 if boucle_auto else 1
    nb_gen, prod_brute_mw, mw_cascade, eclats_cascade, batiments_cascade = 0, 0.0, 0.0, 0, 0
    etapes_res, flux_ext = [], {}
    for _ in range(nb_iter):
        flux_disponibles = dict(flux_disponibles_initiaux)
        nb_gen = nb_gen_fixe if mode == "Parc Fixe (Existant)" else (math.ceil(cible_mw / mw_par_gen) if cible_mw > 0 else 0)
        prod_brute_mw = nb_gen * mw_par_gen
        demandes, flux_ext = {}, {}
        for it, r in spec["conso_gen"]:
            demandes[it] = demandes.get(it, 0.0) + (r * cad_gen * nb_gen)
        for it, r in spec["byproducts_gen"]:
            flux_ext[it] = flux_ext.get(it, 0.0) + (r * cad_gen * nb_gen)
        mw_cascade, eclats_cascade, batiments_cascade = 0.0, 0, 0
        etapes_res = []
        for etape in spec["etapes"]:
            eid = etape["id"]
            try:
                c_et_pct = float(parc_cfg.get("cadences_etapes", {}).get(eid, "100"))
            except ValueError:
                c_et_pct = 100.0
            c_et = c_et_pct / 100.0
            out_item = etape["out_item"]
            besoin_total = max(demandes.get(out_item, 0.0), 0.0)
            fourni_existant = min(besoin_total, flux_disponibles.get(out_item, 0.0))
            if fourni_existant > 0:
                flux_disponibles[out_item] -= fourni_existant
                flux_ext[out_item] = flux_ext.get(out_item, 0.0) - fourni_existant
            besoin_item = besoin_total - fourni_existant
            demandes[out_item] = besoin_item
            try:
                qte_man = int(str(qtes_manuelles.get(eid, "0")).strip())
            except ValueError:
                qte_man = 0
            m_nom = etape["machine"]
            purete = parc_cfg.get("puretes_etapes", {}).get(eid, "Normal (1.0x)")
            mult_purete = MULTIPLICATEUR_PURETE.get(purete, 1.0)
            out_rate_effectif = etape["out_rate"] * mult_purete
            if "Foreuse Mk." in m_nom:
                tier_f = m_nom.split()[-1]
                conso_base, vitesse_mod = ENERGIE_FOREUSE.get(tier_f, 12.0), 1.0
            else:
                m_spec = get_machine_specs(m_nom)
                conso_base, vitesse_mod = float(m_spec.get("mw", 20.0)), float(m_spec.get("vitesse", 1.0))
            if c_et <= 0 or (besoin_item <= 0 and qte_man <= 0):
                etapes_res.append({
                    "nb_ceil": 0, "nb_exact": 0.0, "charge": 0.0, "mw": 0.0,
                    "eclats": 0, "besoin": besoin_total, "fourni_existant": fourni_existant,
                    "besoin_restant": besoin_item, "out_item": out_item,
                    "manuel": False, "machine": m_nom
                })
                continue
            prod_unit = out_rate_effectif * vitesse_mod * c_et
            nb_exact = besoin_item / prod_unit if prod_unit > 0 else 0.0
            if mode == "Parc Fixe (Existant)" and qte_man > 0:
                nb_ceil = qte_man
                prod_reelle = nb_ceil * prod_unit
                ecart_item = prod_reelle - besoin_item
                if abs(ecart_item) > 0.01:
                    flux_ext[out_item] = flux_ext.get(out_item, 0.0) + ecart_item
                cycles = prod_reelle / out_rate_effectif
                charge = (nb_exact / nb_ceil) * 100.0 if nb_ceil > 0 else 0.0
                est_man = True
            else:
                nb_ceil = math.ceil(nb_exact)
                cycles = besoin_item / out_rate_effectif
                charge = (nb_exact / nb_ceil) * 100.0 if nb_ceil > 0 else 0.0
                est_man = False
            mw_e = nb_ceil * conso_base * (c_et ** exp_surc)
            mw_cascade += mw_e
            batiments_cascade += nb_ceil
            sh_e = calculer_eclats_machine(c_et_pct) * nb_ceil
            eclats_cascade += sh_e
            for in_it, in_r in etape["inputs"]:
                demandes[in_it] = demandes.get(in_it, 0.0) + (in_r * cycles)
            for by_it, by_r in etape["byproducts"]:
                flux_ext[by_it] = flux_ext.get(by_it, 0.0) + (by_r * cycles)
            demandes[out_item] = 0.0
            etapes_res.append({
                "nb_ceil": nb_ceil, "nb_exact": nb_exact, "charge": charge, "mw": mw_e,
                "eclats": sh_e, "besoin": besoin_total, "fourni_existant": fourni_existant,
                "besoin_restant": besoin_item, "out_item": out_item,
                "manuel": est_man, "machine": m_nom
            })
        for it_rem, val_rem in demandes.items():
            if val_rem > 0.001:
                flux_ext[it_rem] = flux_ext.get(it_rem, 0.0) - val_rem
        if mode != "Parc Fixe (Existant)" and boucle_auto:
            cible_mw = max(cible_deficit_mw, 0.0) + mw_cascade
    return {
        "nb_gen": nb_gen, "prod_brute_mw": prod_brute_mw, "mw_cascade": mw_cascade,
        "eclats": (eclats_par_gen * nb_gen) + eclats_cascade,
        "batiments": nb_gen + batiments_cascade, "etapes_res": etapes_res, "flux_ext": flux_ext
    }
def simuler_chaine_refined_power(rp_cfg):
    try:
        nb_b = max(int(rp_cfg.get("nb_boiler", "0")), 0)
        f_rate = float(rp_cfg.get("fuel_rate", "0"))
        w_rate = float(rp_cfg.get("water_rate", "0"))
        s_out = float(rp_cfg.get("steam_out", "0"))
        nb_t = max(int(rp_cfg.get("nb_turb", "0")), 0)
        s_req = max(float(rp_cfg.get("steam_req", "1")), 0.1)
        rpm_u = float(rp_cfg.get("rpm_unit", "0"))
        nb_g = max(int(rp_cfg.get("nb_gen", "0")), 0)
        ratio_mw = float(rp_cfg.get("ratio_mw", "0.1"))
    except ValueError:
        return {"mw_prod": 0.0, "mw_conso": 0.0, "vapeur_prod": 0.0, "vapeur_req": 0.0, "rpm_tot": 0.0, "batiments": 0, "flux": {}}
    b_nom = rp_cfg.get("boiler", "")
    mw_conso_b = nb_b * float(get_machine_specs(b_nom).get("mw", 5.0))
    vapeur_prod = nb_b * s_out
    vapeur_req = nb_t * s_req
    ratio_alimentation_vapeur = min(vapeur_prod / vapeur_req, 1.0) if vapeur_req > 0 else 0.0
    rpm_par_turb_reel = rpm_u * ratio_alimentation_vapeur
    rpm_tot = nb_t * rpm_par_turb_reel
    nb_lignes_gen = min(nb_t, nb_g) if nb_t > 0 else 0
    mw_prod = (nb_lignes_gen * rpm_par_turb_reel * ratio_mw) if nb_g <= nb_t else (rpm_tot * ratio_mw)
    flux = {}
    fuel_nom = rp_cfg.get("fuel", "Charbon")
    if nb_b > 0 and f_rate > 0:
        flux[fuel_nom] = flux.get(fuel_nom, 0.0) - (nb_b * f_rate)
    if nb_b > 0 and w_rate > 0:
        flux["Eau"] = flux.get("Eau", 0.0) - (nb_b * w_rate)
    return {
        "mw_prod": mw_prod, "mw_conso": mw_conso_b,
        "vapeur_prod": vapeur_prod, "vapeur_req": vapeur_req,
        "rpm_tot": rpm_tot, "batiments": nb_b + nb_t + nb_g, "flux": flux
    }
labels_flux_bilan = []

def declencher_calcul(*_):
    global dernier_flux_calcule_usine, dernier_flux_calcule_global, dernier_deficit_mw_usine, dernier_deficit_mw_global, job_calcul_debounce, labels_flux_bilan
    job_calcul_debounce = None
    if verrou_chargement_ui:
        return
    synchroniser_usine_active()
    exp_surc = float(MODS_CONFIG.get("exposant_surcadencage", 1.6))
    stats_par_usine = {}
    mw_conso_usines_global = 0.0
    bilan_cloud_digital_storage = {}
    for u_nom, u_dict in usines_data.items():
        u_mw, u_mw_prod_machines, u_eclats, u_somers = 0.0, 0.0, 0, 0
        u_flux = {}
        u_machines, u_bat = compter_machines_usine(u_dict)
        # 1. Ateliers
        for idx_a, a_cfg in enumerate(u_dict.get("ateliers", [])):
            machine = a_cfg.get("machine", "Constructeur")
            rec_nom = a_cfg.get("recette", "")
            try:
                nb_m = max(int(a_cfg.get("qte", "0")), 0)
            except ValueError:
                if u_nom == usine_active_nom and idx_a < len(cartes_ateliers):
                    cartes_ateliers[idx_a].lbl_telemetrie.configure(text="⚠️ Valeur numérique invalide.", text_color=THEME["status_err"])
                continue
            try:
                cad_pct = float(a_cfg.get("cadence", "0"))
                s_used = int(a_cfg.get("somers", "0"))
            except ValueError:
                if u_nom == usine_active_nom and idx_a < len(cartes_ateliers):
                    cartes_ateliers[idx_a].lbl_telemetrie.configure(text="⚠️ Valeur numérique invalide.", text_color=THEME["status_err"])
                continue
            if rec_nom in ["", "-", "Aucune recette"] or nb_m <= 0 or cad_pct <= 0:
                if u_nom == usine_active_nom and idx_a < len(cartes_ateliers):
                    cartes_ateliers[idx_a].lbl_telemetrie.configure(text="⏸️ Atelier en veille (0 MW)", text_color=THEME["text_muted"])
                continue
            rec_match = df[df['Nom de la recette'] == rec_nom]
            if rec_match.empty:
                continue
            rec = rec_match.iloc[0]
            m_specs = get_machine_specs(machine)
            conso_base = float(m_specs.get("mw", 15.0))
            vitesse_mod = float(m_specs.get("vitesse", 1.0))
            s_max = int(m_specs.get("somers_max", 1))
            cad = cad_pct / 100.0
            prod_mult, pwr_mult_somers = calculer_multiplicateurs_somers(s_used, s_max)
            est_prod_mw = (m_specs.get("sens_mw", "Consomme") == "Produit" or m_specs.get("categorie") == "Énergie Directe")
            mw_ligne = (conso_base * cad * nb_m) if est_prod_mw else (conso_base * (cad ** exp_surc) * pwr_mult_somers * nb_m)
            sh_ligne = calculer_eclats_machine(cad_pct) * nb_m
            if est_prod_mw:
                u_mw_prod_machines += mw_ligne
            else:
                u_mw += mw_ligne
            u_eclats += sh_ligne
            u_somers += s_used * nb_m
            res_out, res_in = [], []
            for i_s in [1, 2]:
                s_n, s_v = rec.get(f'Sortie {i_s}'), rec.get(f'Sortie {i_s} / Min')
                if pd.notna(s_n) and pd.notna(s_v) and s_v > 0:
                    d_out = s_v * vitesse_mod * cad * prod_mult * nb_m
                    u_flux[s_n] = u_flux.get(s_n, 0.0) + d_out
                    res_out.append(f"+{d_out:.1f} {s_n}")
            for i_e in [1, 2, 3, 4]:
                e_n, e_v = rec.get(f'Entrée {i_e}'), rec.get(f'Entrée {i_e} / Min')
                if pd.notna(e_n) and pd.notna(e_v) and e_v > 0:
                    d_in = e_v * vitesse_mod * cad * nb_m
                    u_flux[e_n] = u_flux.get(e_n, 0.0) - d_in
                    res_in.append(f"-{d_in:.1f} {e_n}")
            if u_nom == usine_active_nom and idx_a < len(cartes_ateliers):
                cartes_ateliers[idx_a].lbl_telemetrie.configure(
                    text=f"⚡ {mw_ligne:.1f} MW │ 🔋 {sh_ligne} Éclat(s) │ 🌀 Prod x{prod_mult:.2f} │ Vitesse x{vitesse_mod:.2f} │ IN: {', '.join(res_in) if res_in else '—'} ➔ OUT: {', '.join(res_out)}",
                    text_color=THEME["text_main"]
                )
        # 2. Foreuses & Extracteurs (Vanilla + Moddés)
        for idx_f, f_cfg in enumerate(u_dict.get("foreuses", [])):
            machine = f_cfg.get("machine", "Foreuse")
            tier = f_cfg.get("tier", "Mk.2")
            purete = f_cfg.get("purete", "Normal (1.0x)")
            ressource = f_cfg.get("ressource", "Minerai de fer")
            try:
                nb_m = max(int(f_cfg.get("qte", "0")), 0)
            except ValueError:
                continue
            try:
                cad_pct = float(f_cfg.get("cadence", "0"))
            except ValueError:
                continue
            if nb_m <= 0 or cad_pct <= 0:
                if u_nom == usine_active_nom and idx_f < len(cartes_foreuses):
                    cartes_foreuses[idx_f].lbl_telemetrie.configure(text="⏸️ Extracteur en veille (0 MW)", text_color=THEME["text_muted"])
                continue
            cad = cad_pct / 100.0
            mult_pur = MULTIPLICATEUR_PURETE.get(purete, 1.0)
            prod_mult, pwr_mult_somers = calculer_multiplicateurs_somers(0, 0)
            if machine == "Foreuse":
                base_mw = ENERGIE_FOREUSE.get(tier, 12.0)
                base_prod = PROD_FOREUSE_BASE.get(tier, 120.0) * mult_pur
            elif machine == "Pompe à eau":
                m_sp = get_machine_specs("Pompe à eau")
                base_mw = float(m_sp.get("mw", 20.0))
                base_prod = float(m_sp.get("valeur_spec", 120.0)) * float(m_sp.get("vitesse", 1.0))
            else:
                m_sp = get_machine_specs(machine)
                base_mw = float(m_sp.get("mw", 40.0))
                debit_spec = float(m_sp.get("valeur_spec", 120.0))
                base_prod = (debit_spec if debit_spec > 0 else 120.0) * mult_pur * float(m_sp.get("vitesse", 1.0))
            mw_ligne = base_mw * (cad ** exp_surc) * pwr_mult_somers * nb_m
            debit_ext = base_prod * cad * prod_mult * nb_m
            sh_ligne = calculer_eclats_machine(cad_pct) * nb_m
            u_mw += mw_ligne
            u_eclats += sh_ligne
            u_flux[ressource] = u_flux.get(ressource, 0.0) + debit_ext
            if u_nom == usine_active_nom and idx_f < len(cartes_foreuses):
                cartes_foreuses[idx_f].lbl_telemetrie.configure(
                    text=f"⚡ {mw_ligne:.1f} MW │ 🔋 {sh_ligne} Éclat(s) │ 🌀 Prod x{prod_mult:.2f} │ ⛏️ +{debit_ext:.1f} {ressource} / min",
                    text_color=THEME["status_ok"]
                )
        # 3. Digital Storage (Infrastructure + Flux Cloud)
        ds_cfg = u_dict.get("digital_storage", {})
        ds_mw, ds_cap, ds_bw_max, ds_bw_used = 0.0, 0, 0.0, 0.0
        for idx_eq, eq in enumerate(ds_cfg.get("equipements", [])):
            try:
                q_e = max(int(eq.get("qte", "0")), 0)
                mw_e = float(eq.get("mw_unit", "0"))
                bw_e = float(eq.get("bande_passante", "0"))
                slots_baie = 0
                erreurs_baie = []
                if eq.get("type") == DS_TYPE_BAIE:
                    cap_e, _, slots_baie, erreurs_baie = resumer_baie_ds(eq)
                    if erreurs_baie:
                        cap_e = 0
                else:
                    cap_e = int(float(eq.get("capacite_items", "0")))
            except ValueError:
                continue
            if u_nom == usine_active_nom and idx_eq < len(cartes_ds_equip):
                cartes_ds_equip[idx_eq].maj_resume_baie(erreurs_baie, cap_e, slots_baie)
            ds_mw += q_e * mw_e
            ds_cap += q_e * cap_e
            ds_bw_max += q_e * bw_e
        for fl in ds_cfg.get("flux_cloud", []):
            it_c = fl.get("item", "")
            sens = fl.get("sens", "")
            try:
                deb_c = max(float(fl.get("debit", "0")), 0.0)
            except ValueError:
                deb_c = 0.0
            if not it_c or deb_c <= 0:
                continue
            ds_bw_used += deb_c
            if "Upload" in sens:
                u_flux[it_c] = u_flux.get(it_c, 0.0) - deb_c
                bilan_cloud_digital_storage[it_c] = bilan_cloud_digital_storage.get(it_c, 0.0) + deb_c
            else:
                u_flux[it_c] = u_flux.get(it_c, 0.0) + deb_c
                bilan_cloud_digital_storage[it_c] = bilan_cloud_digital_storage.get(it_c, 0.0) - deb_c
        u_mw += ds_mw
        if u_nom == usine_active_nom and lbl_bilan_ds_header is not None:
            statut_bw = "🟢 OK" if ds_bw_used <= ds_bw_max or ds_bw_max == 0 else "🔴 SATURÉE"
            lbl_bilan_ds_header.configure(
                text=f"🌐 RÉSEAU DIGITAL STORAGE ({u_nom})  │  ⚡ Conso : {ds_mw:.1f} MW  │  💾 Capacité : {ds_cap:,} items  │  📡 Bande Passante : {ds_bw_used:.1f} / {ds_bw_max:.1f} /min ({statut_bw})"
            )
        stats_par_usine[u_nom] = {
            "mw_usine": u_mw, "mw_cascade": 0.0, "mw_prod": u_mw_prod_machines,
            "eclats": u_eclats, "somers": u_somers, "batiments": u_bat,
            "flux": u_flux, "machines": u_machines
        }
        mw_conso_usines_global += u_mw
    # 4. Chaînes Refined Power (Vapeur ➔ RPM ➔ MW)
    mw_prod_global = sum(v["mw_prod"] for v in stats_par_usine.values())
    mw_cascade_global = 0.0
    for u_nom, u_dict in usines_data.items():
        for idx_rp, rp_cfg in enumerate(u_dict.get("refined_power", [])):
            res_rp = simuler_chaine_refined_power(rp_cfg)
            stats_par_usine[u_nom]["mw_prod"] += res_rp["mw_prod"]
            stats_par_usine[u_nom]["mw_cascade"] += res_rp["mw_conso"]
            stats_par_usine[u_nom]["batiments"] += res_rp["batiments"]
            for champ_nom, champ_qte in (("boiler", "nb_boiler"), ("turbine", "nb_turb"), ("gen", "nb_gen")):
                try:
                    qte_bat = max(int(rp_cfg.get(champ_qte, "0")), 0)
                except (TypeError, ValueError):
                    qte_bat = 0
                ajouter_compteur_machine(stats_par_usine[u_nom]["machines"], rp_cfg.get(champ_nom, ""), qte_bat)
            for k_f, v_f in res_rp["flux"].items():
                stats_par_usine[u_nom]["flux"][k_f] = stats_par_usine[u_nom]["flux"].get(k_f, 0.0) + v_f
            mw_prod_global += res_rp["mw_prod"]
            mw_cascade_global += res_rp["mw_conso"]
            if u_nom == usine_active_nom and idx_rp < len(cartes_refined_power):
                c_rp = cartes_refined_power[idx_rp]
                c_rp.badge_mw.configure(text=f"🌀 {res_rp['rpm_tot']:.0f} RPM  ➔  ⚡ +{res_rp['mw_prod']:.1f} MW")
                c_rp.lbl_details.configure(
                    text=f"💨 Vapeur produite : {res_rp['vapeur_prod']:.1f} m³/min (Requise : {res_rp['vapeur_req']:.1f} m³/min)  │  ⚙️ Rotation : {res_rp['rpm_tot']:.0f} RPM  │  ⚡ Conso Chaudières : {res_rp['mw_conso']:.1f} MW"
                )
    flux_disponible_par_usine = {
        nom: {item: max(qte, 0.0) for item, qte in stats["flux"].items() if qte > 0}
        for nom, stats in stats_par_usine.items()
    }
    flux_net_initial = {}
    for stats in stats_par_usine.values():
        for item, qte in stats["flux"].items():
            flux_net_initial[item] = flux_net_initial.get(item, 0.0) + qte
    flux_disponible_global = {item: max(qte, 0.0) for item, qte in flux_net_initial.items()}

    def appliquer_flux_parc_energetique(nom_usine, portee_ressources, flux):
        for item, variation in flux.items():
            if variation >= 0:
                stats_par_usine[nom_usine]["flux"][item] = stats_par_usine[nom_usine]["flux"].get(item, 0.0) + variation
                flux_disponible_par_usine[nom_usine][item] = flux_disponible_par_usine[nom_usine].get(item, 0.0) + variation
                flux_disponible_global[item] = flux_disponible_global.get(item, 0.0) + variation
                continue
            besoin = -variation
            if portee_ressources == "Réseau Global":
                restant_a_puiser = min(besoin, flux_disponible_global.get(item, 0.0))
                fournisseurs = [nom_usine] + [nom for nom in stats_par_usine if nom != nom_usine]
                for nom_fournisseur in fournisseurs:
                    disponible = flux_disponible_par_usine[nom_fournisseur].get(item, 0.0)
                    utilise = min(disponible, restant_a_puiser)
                    if utilise > 0:
                        flux_disponible_par_usine[nom_fournisseur][item] = disponible - utilise
                        stats_par_usine[nom_fournisseur]["flux"][item] -= utilise
                        restant_a_puiser -= utilise
                    if restant_a_puiser <= 0.001:
                        break
                utilise = min(besoin, flux_disponible_global.get(item, 0.0))
                flux_disponible_global[item] = max(flux_disponible_global.get(item, 0.0) - besoin, 0.0)
                non_couvert = besoin - utilise
                if non_couvert > 0:
                    stats_par_usine[nom_usine]["flux"][item] = stats_par_usine[nom_usine]["flux"].get(item, 0.0) - non_couvert
            else:
                disponible = flux_disponible_par_usine[nom_usine].get(item, 0.0)
                utilise = min(besoin, disponible)
                flux_disponible_par_usine[nom_usine][item] = disponible - utilise
                flux_disponible_global[item] = max(flux_disponible_global.get(item, 0.0) - besoin, 0.0)
                stats_par_usine[nom_usine]["flux"][item] = stats_par_usine[nom_usine]["flux"].get(item, 0.0) - besoin

    # 5. Parcs Énergétiques Passe 1 : Parcs Fixes
    for u_nom, u_dict in usines_data.items():
        for idx_p, p_cfg in enumerate(u_dict.get("parcs_energie", [])):
            if p_cfg.get("mode") == "Parc Fixe (Existant)":
                portee_ressources = p_cfg.get("portee_auto", "Réseau Global")
                flux_source = flux_disponible_par_usine[u_nom] if portee_ressources == "Usine Active" else flux_disponible_global
                res_p = simuler_parc_energetique(p_cfg, 0.0, flux_source)
                stats_par_usine[u_nom]["mw_prod"] += res_p["prod_brute_mw"]
                stats_par_usine[u_nom]["mw_cascade"] += res_p["mw_cascade"]
                stats_par_usine[u_nom]["eclats"] += res_p["eclats"]
                stats_par_usine[u_nom]["batiments"] += res_p["batiments"]
                ajouter_compteur_machine(stats_par_usine[u_nom]["machines"], p_cfg.get("filiere", ""), res_p["nb_gen"])
                for etape_res in res_p["etapes_res"]:
                    ajouter_compteur_machine(stats_par_usine[u_nom]["machines"], etape_res["machine"], etape_res["nb_ceil"])
                appliquer_flux_parc_energetique(u_nom, portee_ressources, res_p["flux_ext"])
                mw_prod_global += res_p["prod_brute_mw"]
                mw_cascade_global += res_p["mw_cascade"]
                if u_nom == usine_active_nom and idx_p < len(cartes_parcs_energie):
                    maj_ui_carte_parc(cartes_parcs_energie[idx_p], res_p)
    # 6. Parcs Énergétiques Passe 2 : Auto-Compensation
    for u_nom, u_dict in usines_data.items():
        for idx_p, p_cfg in enumerate(u_dict.get("parcs_energie", [])):
            if p_cfg.get("mode") != "Parc Fixe (Existant)":
                portee = p_cfg.get("portee_auto", "Réseau Global")
                if portee == "Usine Active":
                    deficit_cible = (stats_par_usine[u_nom]["mw_usine"] + stats_par_usine[u_nom]["mw_cascade"]) - stats_par_usine[u_nom]["mw_prod"]
                else:
                    deficit_cible = (mw_conso_usines_global + mw_cascade_global) - mw_prod_global
                flux_source = flux_disponible_par_usine[u_nom] if portee == "Usine Active" else flux_disponible_global
                res_p = simuler_parc_energetique(p_cfg, max(deficit_cible, 0.0), flux_source)
                stats_par_usine[u_nom]["mw_prod"] += res_p["prod_brute_mw"]
                stats_par_usine[u_nom]["mw_cascade"] += res_p["mw_cascade"]
                stats_par_usine[u_nom]["eclats"] += res_p["eclats"]
                stats_par_usine[u_nom]["batiments"] += res_p["batiments"]
                ajouter_compteur_machine(stats_par_usine[u_nom]["machines"], p_cfg.get("filiere", ""), res_p["nb_gen"])
                for etape_res in res_p["etapes_res"]:
                    ajouter_compteur_machine(stats_par_usine[u_nom]["machines"], etape_res["machine"], etape_res["nb_ceil"])
                appliquer_flux_parc_energetique(u_nom, portee, res_p["flux_ext"])
                mw_prod_global += res_p["prod_brute_mw"]
                mw_cascade_global += res_p["mw_cascade"]
                if u_nom == usine_active_nom and idx_p < len(cartes_parcs_energie):
                    maj_ui_carte_parc(cartes_parcs_energie[idx_p], res_p)
    if lbl_cloud_global_ds is not None:
        l_cloud = [f"• {k} : {v:+.1f} /min dans le Cloud" for k, v in sorted(bilan_cloud_digital_storage.items()) if abs(v) > 0.05]
        lbl_cloud_global_ds.configure(text="☁️ État du Stockage Cloud Inter-Usines :  " + ("  │  ".join(l_cloud) if l_cloud else "Équilibré (ou aucun flux Cloud actif)"))
    st_active = stats_par_usine.get(usine_active_nom, {"mw_usine": 0.0, "mw_cascade": 0.0, "mw_prod": 0.0, "eclats": 0, "somers": 0, "batiments": 0, "flux": {}, "machines": {}})
    demande_active_tot = st_active["mw_usine"] + st_active["mw_cascade"]
    demande_globale_tot = mw_conso_usines_global + mw_cascade_global
    marge_globale_mw = mw_prod_global - demande_globale_tot
    dernier_deficit_mw_usine = max(0.0, demande_active_tot - st_active["mw_prod"])
    dernier_deficit_mw_global = max(0.0, demande_globale_tot - mw_prod_global)
    lbl_val_mw_usine_active.configure(text=f"{demande_active_tot:.1f} MW (Prod locale : {st_active['mw_prod']:.1f} MW)")
    lbl_val_mw_conso_globale.configure(text=f"{demande_globale_tot:.1f} MW (dont Cascade : {mw_cascade_global:.1f} MW)")
    lbl_val_mw_prod_globale.configure(text=f"{mw_prod_global:.1f} MW")
    if mw_prod_global > 0:
        ratio = min(demande_globale_tot / mw_prod_global, 1.0)
        jauge_reseau.set(ratio)
        if marge_globale_mw >= -0.05:
            jauge_reseau.configure(progress_color=THEME["status_ok"])
            lbl_statut_reseau.configure(text=f"🟢 RÉSEAU GLOBAL STABLE — Marge : +{marge_globale_mw:.1f} MW ({(demande_globale_tot/mw_prod_global)*100:.1f}%)", text_color=THEME["status_ok"])
        else:
            jauge_reseau.configure(progress_color=THEME["status_err"])
            lbl_statut_reseau.configure(text=f"🔴 DÉFICIT RÉSEAU GLOBAL : {marge_globale_mw:.1f} MW", text_color=THEME["status_err"])
    else:
        jauge_reseau.set(0.0)
        lbl_statut_reseau.configure(text=f"🔴 AUCUNE CENTRALE ACTIVE — Manque {demande_globale_tot:.1f} MW" if demande_globale_tot > 0 else "⚪ Réseau en attente", text_color=THEME["status_err"] if demande_globale_tot > 0 else THEME["text_muted"])
    flux_global_combine = {}
    for v in stats_par_usine.values():
        for k_it, v_it in v["flux"].items():
            flux_global_combine[k_it] = flux_global_combine.get(k_it, 0.0) + v_it
    dernier_flux_calcule_usine = dict(st_active["flux"])
    dernier_flux_calcule_global = dict(flux_global_combine)
    if portee_bilan_var.get() == "🏭 Usine Active":
        kpi_ec, kpi_so, kpi_ba, flux_affiche = st_active["eclats"], st_active["somers"], st_active["batiments"], dernier_flux_calcule_usine
    else:
        kpi_ec = sum(v["eclats"] for v in stats_par_usine.values())
        kpi_so = sum(v["somers"] for v in stats_par_usine.values())
        kpi_ba = sum(v["batiments"] for v in stats_par_usine.values())
        flux_affiche = dernier_flux_calcule_global
    lbl_kpi_eclats.configure(text=str(kpi_ec))
    lbl_kpi_somers.configure(text=str(kpi_so))
    lbl_kpi_batiments.configure(text=str(kpi_ba))
    compteurs_affiches = dict(st_active["machines"]) if portee_bilan_var.get() == "🏭 Usine Active" else {}
    if portee_bilan_var.get() != "🏭 Usine Active":
        for stats in stats_par_usine.values():
            for nom_machine, nombre in stats["machines"].items():
                ajouter_compteur_machine(compteurs_affiches, nom_machine, nombre)
    if lbl_resume_machines is not None:
        lbl_resume_machines.configure(state="normal")
        lbl_resume_machines.delete("1.0", "end")
        lignes_machines = [f"• {nom} : {nombre}" for nom, nombre in sorted(compteurs_affiches.items()) if nombre > 0]
        lbl_resume_machines.insert("1.0", "\n".join(lignes_machines) if lignes_machines else "Aucun bâtiment dans cette usine.")
        lbl_resume_machines.configure(state="disabled")
    if lbl_cout_construction is not None:
        couts_totaux, sans_recette = calculer_couts_construction(compteurs_affiches, MODS_CONFIG.get("couts_construction", {}))
        portee_couts = "Usine active" if portee_bilan_var.get() == "🏭 Usine Active" else "Toutes les usines"
        lignes_couts = [f"Coût total — {portee_couts} :"]
        lignes_couts.extend(f"• {nom} : {qte:g}" for nom, qte in sorted(couts_totaux.items()))
        if sans_recette:
            manquants = ", ".join(f"{nom} ({qte})" for nom, qte in sorted(sans_recette)[:5])
            lignes_couts.append(f"À renseigner : {manquants}")
        if not couts_totaux and not sans_recette:
            lignes_couts.append("Ajoute les coûts des bâtiments pour voir les matériaux nécessaires.")
        lbl_cout_construction.configure(text="\n".join(lignes_couts))
    mode_f = filtre_bilan_var.get()
    for widget in lbl_flux_global.winfo_children():
        widget.destroy()
    labels_flux_bilan = []
    for item, net in sorted(flux_affiche.items()):
        est_equilibre = abs(net) < 0.05
        if mode_f == "Déficits 🔴" and (net >= 0 or est_equilibre):
            continue
        if mode_f == "Surplus 🟢" and (net <= 0 or est_equilibre):
            continue
        if est_equilibre:
            statut, couleur = "equilibre", THEME["text_main"]
            texte = f"⚪ [ÉQUILIBRE]  {0.0:+8.2f} /min  │  {item}"
        elif net > 0:
            statut, couleur = "surplus", THEME["status_ok"]
            texte = f"🟢 [SURPLUS]  {net:+8.2f} /min  │  {item}"
        else:
            statut, couleur = "deficit", THEME["status_err"]
            texte = f"🔴 [DÉFICIT]  {net:+8.2f} /min  │  {item}"
        label = ctk.CTkLabel(
            lbl_flux_global, text=texte, justify="left", anchor="w",
            font=ctk.CTkFont(family="Consolas", size=12),
            text_color=couleur, wraplength=950
        )
        label.pack(fill="x", padx=8, pady=2)
        labels_flux_bilan.append((label, statut))
    if not labels_flux_bilan:
        label = ctk.CTkLabel(
            lbl_flux_global, text="✅ Aucun flux dans ce filtre.",
            justify="left", anchor="w", text_color=THEME["text_main"]
        )
        label.pack(fill="x", padx=8, pady=8)
        labels_flux_bilan.append((label, "equilibre"))
    rafraichir_liste_deficits_ui()
def maj_ui_carte_parc(carte_p, res_p):
    carte_p.badge_bilan_parc.configure(text=f"{res_p['nb_gen']}x Centrale(s) ➔ +{res_p['prod_brute_mw']:.1f} MW (Conso cascade : {res_p['mw_cascade']:.1f} MW)")
    for idx_w, w_info in enumerate(carte_p.widgets_etapes):
        if idx_w < len(res_p["etapes_res"]):
            er = res_p["etapes_res"][idx_w]
            tag_m = "MANUEL" if er.get("manuel") else "AUTO"
            w_info["lbl_res"].configure(text=f"[{tag_m}] {er['nb_ceil']}x machine(s) à ajouter (besoin exact : {er['nb_exact']:.2f}x)")
            w_info["lbl_flux"].configure(
                text=f"Besoin : {er['besoin']:.1f} {er['out_item']}/min │ "
                f"Déjà disponible : {er.get('fourni_existant', 0.0):.1f}/min │ "
                f"À produire : {er.get('besoin_restant', er['besoin']):.1f}/min │ "
                f"⚡ {er['mw']:.1f} MW │ 🔋 {er['eclats']} Éclat(s)"
            )
# ==============================================================================
# 10. GESTION DES USINES & DOSSIERS DÉDIÉS DANS DOCUMENTS
# ==============================================================================
def charger_usine_dans_ui(nom_usine):
    global usine_active_nom, verrou_chargement_ui
    verrou_chargement_ui = True
    usine_active_nom = nom_usine
    USER_SETTINGS["derniere_usine_active"] = nom_usine
    sauvegarder_settings()
    for lst in (cartes_ateliers, cartes_foreuses, cartes_parcs_energie, cartes_refined_power, cartes_ds_equip, cartes_ds_flux):
        for c in list(lst):
            c.destroy()
        lst.clear()
    u_dict = usines_data.get(nom_usine, creer_structure_usine_vide())
    for idx, a_data in enumerate(u_dict.get("ateliers", []), start=1):
        c = CarteAtelierModulaire(scroll_ateliers, idx, init_data=a_data)
        cartes_ateliers.append(c)
    organiser_cartes_grille(cartes_ateliers, scroll_ateliers)
    for idx, f_data in enumerate(u_dict.get("foreuses", []), start=1):
        c = CarteForeuseModulaire(scroll_foreuses, idx, init_data=f_data)
        cartes_foreuses.append(c)
    organiser_cartes_grille(cartes_foreuses, scroll_foreuses)
    for idx, p_data in enumerate(u_dict.get("parcs_energie", []), start=1):
        c = CarteParcEnergetique(scroll_parcs_energie, idx, init_data=p_data)
        c.pack(fill="x", padx=8, pady=8)
        cartes_parcs_energie.append(c)
    for idx, rp_data in enumerate(u_dict.get("refined_power", []), start=1):
        c = CarteRefinedPower(scroll_parcs_energie, idx, init_data=rp_data)
        c.pack(fill="x", padx=8, pady=8)
        cartes_refined_power.append(c)
    ds_d = u_dict.get("digital_storage", creer_structure_usine_vide()["digital_storage"])
    for eq_data in ds_d.get("equipements", []):
        c = CarteEquipementDigitalStorage(frame_ds_equip_list, init_data=eq_data)
        c.pack(fill="x", padx=8, pady=4)
        cartes_ds_equip.append(c)
    for fl_data in ds_d.get("flux_cloud", []):
        c = CarteFluxDigitalStorage(frame_ds_flux_list, init_data=fl_data)
        c.pack(fill="x", padx=8, pady=4)
        cartes_ds_flux.append(c)
    verrou_chargement_ui = False
    declencher_calcul()
def changer_usine_selectionnee(nouveau_nom):
    synchroniser_usine_active()
    charger_usine_dans_ui(nouveau_nom)
def ouvrir_dossier_usine_active():
    synchroniser_usine_active()
    d = obtenir_dossier_usine(usine_active_nom)
    if os.name == "nt":
        os.startfile(d)
    else:
        popup_info("Dossier Usine", f"Dossier de l'usine :\n{d}")
def creer_nouvelle_usine():
    synchroniser_usine_active()
    nom = popup_askstring("Nouvelle Usine", "Nom de l'usine (créera un dossier dédié dans Documents/Nexus_Industrial_Architect/Usines/) :")
    if not nom or not nom.strip():
        return
    nom = nom.strip()
    if nom in usines_data:
        popup_warning("Usine existante", f"Une usine nommée '{nom}' existe déjà.")
        return
    usines_data[nom] = creer_structure_usine_vide()
    sauvegarder_usine_dans_son_dossier(nom, usines_data[nom])
    menu_usine_active.configure(values=list(usines_data.keys()))
    menu_usine_active.set(nom)
    charger_usine_dans_ui(nom)
    popup_success("Usine créée", f"Dossier créé dans Documents :\nUsines\\{nettoyer_nom_dossier(nom)}")
def renommer_usine_courante():
    global usine_active_nom
    synchroniser_usine_active()
    nouveau = popup_askstring("Renommer l'Usine", f"Nouveau nom pour '{usine_active_nom}' :", initialvalue=usine_active_nom)
    if not nouveau or nouveau.strip() == usine_active_nom:
        return
    nouveau = nouveau.strip()
    if nouveau in usines_data:
        popup_warning("Usine existante", f"Une usine nommée '{nouveau}' existe déjà.")
        return
    ancien_dossier = obtenir_dossier_usine(usine_active_nom)
    usines_data[nouveau] = usines_data.pop(usine_active_nom)
    usine_active_nom = nouveau
    sauvegarder_usine_dans_son_dossier(nouveau, usines_data[nouveau])
    if os.path.exists(ancien_dossier) and ancien_dossier != obtenir_dossier_usine(nouveau):
        shutil.rmtree(ancien_dossier, ignore_errors=True)
    menu_usine_active.configure(values=list(usines_data.keys()))
    menu_usine_active.set(nouveau)
    declencher_calcul()
def supprimer_usine_courante():
    if len(usines_data) <= 1:
        popup_warning("Action impossible", "Vous devez conserver au moins une usine active.")
        return
    if not popup_askyesno("Supprimer l'Usine", f"Supprimer l'usine '{usine_active_nom}' ainsi que son dossier dans Documents ?"):
        return
    d_del = obtenir_dossier_usine(usine_active_nom)
    usines_data.pop(usine_active_nom, None)
    shutil.rmtree(d_del, ignore_errors=True)
    premiere = list(usines_data.keys())[0]
    menu_usine_active.configure(values=list(usines_data.keys()))
    menu_usine_active.set(premiere)
    charger_usine_dans_ui(premiere)
# ==============================================================================
# 11. INTERFACE PRINCIPALE (BARRE D'USINES, 6 ONGLETS, COCKPIT)
# ==============================================================================
header = ctk.CTkFrame(app, fg_color=THEME["bg_panel"], corner_radius=0, height=62)
header.pack(fill="x", padx=0, pady=0)
lbl_main_title = ctk.CTkLabel(header, text=f"⚙️ {NOM_LOGICIEL}", font=ctk.CTkFont(family="Consolas", size=17, weight="bold"), text_color=THEME["text_main"])
lbl_main_title.pack(side="left", padx=(16, 10), pady=12)
bar_usines = ctk.CTkFrame(header, fg_color=THEME["bg_card_alt"], corner_radius=10)
bar_usines.pack(side="left", padx=4, pady=8)
lbl_usine_active_hdr = ctk.CTkLabel(bar_usines, text="🏭 Usine :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"])
lbl_usine_active_hdr.pack(side="left", padx=(10, 4), pady=6)
menu_usine_active = ctk.CTkOptionMenu(bar_usines, values=list(usines_data.keys()), width=190, corner_radius=8, fg_color=THEME["tab_sel"], button_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=changer_usine_selectionnee)
menu_usine_active.pack(side="left", padx=4, pady=6)
menu_usine_active.set(usine_active_nom)
ctk.CTkButton(bar_usines, text="+ Nouvelle", width=90, height=28, corner_radius=8, fg_color="#065F46", hover_color="#047857", text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), command=creer_nouvelle_usine).pack(side="left", padx=3, pady=6)
ctk.CTkButton(bar_usines, text="✏️ Renommer", width=90, height=28, corner_radius=8, fg_color="#334155", hover_color="#475569", text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), command=renommer_usine_courante).pack(side="left", padx=3, pady=6)
ctk.CTkButton(bar_usines, text="🗑️ Supprimer", width=90, height=28, corner_radius=8, fg_color="#991B1B", hover_color="#7F1D1D", text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), command=supprimer_usine_courante).pack(side="left", padx=3, pady=6)
ctk.CTkButton(bar_usines, text="📂 Dossier Usine", width=115, height=28, corner_radius=8, fg_color=THEME["seg_sel"], hover_color=THEME["tab_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), command=ouvrir_dossier_usine_active).pack(side="left", padx=(3, 8), pady=6)
def sauvegarder_projet_complet():
    synchroniser_usine_active()
    payload = {"ficsmas": ficsmas_actif.get(), "usine_active": usine_active_nom, "usines_data": usines_data, "mods_config": MODS_CONFIG}
    ch = filedialog.asksaveasfilename(initialdir=DOSSIER_RACINE_DOCS, defaultextension=".json", filetypes=[("Archive Globale Nexus", "*.json")])
    if ch:
        with open(ch, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        popup_success("Export réussi", f"Archive complète exportée :\n{ch}")
def charger_projet_complet():
    global usines_data, usine_active_nom
    ch = filedialog.askopenfilename(initialdir=DOSSIER_RACINE_DOCS, filetypes=[("Archive Globale Nexus", "*.json")])
    if not ch:
        return
    try:
        with open(ch, "r", encoding="utf-8") as f:
            payload = json.load(f)
        ficsmas_actif.set(payload.get("ficsmas", False))
        if "mods_config" in payload:
            MODS_CONFIG.update(payload["mods_config"])
            sauvegarder_mods()
            charger_et_fusionner_donnees()
        if "usines_data" in payload and payload["usines_data"]:
            usines_data = payload["usines_data"]
            for un, ud in usines_data.items():
                sauvegarder_usine_dans_son_dossier(un, ud)
            usine_active_nom = payload.get("usine_active", list(usines_data.keys())[0])
        menu_usine_active.configure(values=list(usines_data.keys()))
        menu_usine_active.set(usine_active_nom)
        charger_usine_dans_ui(usine_active_nom)
        construire_onglet_mods()
        construire_onglet_auto()
        popup_success("Import réussi", "Toutes les usines ont été importées et synchronisées dans Documents !")
    except Exception as e:
        popup_error("Erreur d'import", f"Fichier invalide :\n{e}")
workspace = ctk.CTkFrame(app, fg_color=THEME["bg_main"], corner_radius=0)
workspace.pack(fill="both", expand=True, padx=14, pady=10)
tabs = ctk.CTkTabview(
    workspace, fg_color=THEME["bg_panel"],
    segmented_button_fg_color=THEME["bg_card_alt"],
    segmented_button_selected_color=THEME["tab_sel"],
    segmented_button_selected_hover_color=THEME["seg_sel"],
    text_color="#FFFFFF", corner_radius=12
)
tabs.pack(side="left", fill="both", expand=True, padx=(0, 12))
tab_prod = tabs.add("🏭 1. ATELIERS")
tab_ext = tabs.add("⛏️ 2. FOREUSES")
tab_pwr = tabs.add("⚡ 3. ÉNERGIE & REFINED POWER")
tab_auto = tabs.add("🎯 4. AUTO-SOLVEUR")
tab_ds = tabs.add("🌐 5. DIGITAL STORAGE")
tab_mods = tabs.add("🧬 6. MODS & LABO")
tab_recettes = tabs.add("📚 7. RECETTES & STACKS")
tab_wiki = tabs.add("📖 8. WIKI & IMAGES")

cadres_descriptions_onglets = []

def ajouter_description_onglet(parent, texte):
    aide = ctk.CTkFrame(parent, fg_color=THEME["bg_card_alt"], corner_radius=8)
    aide.pack(fill="x", padx=8, pady=(6, 2))
    cadres_descriptions_onglets.append(aide)
    ctk.CTkLabel(aide, text=texte, justify="left", anchor="w", wraplength=950, text_color=THEME["text_main"]).pack(side="left", fill="x", expand=True, padx=10, pady=7)
    ajouter_bouton_aide(aide, texte)

def changer_mode_affichage(value):
    USER_SETTINGS["mode_affichage_cartes"] = value
    sauvegarder_settings()
    for carte in cartes_ateliers + cartes_foreuses:
        carte.basculer_details(value == "Cartes")
    organiser_cartes_grille(cartes_ateliers, scroll_ateliers)
    organiser_cartes_grille(cartes_foreuses, scroll_foreuses)

ajouter_description_onglet(tab_prod, "Ici, tu choisis les machines qui fabriquent des objets. Exemple : 3 constructeurs fabriquent des vis.")
ajouter_description_onglet(tab_ext, "Ici, tu choisis les machines qui sortent des ressources du sol. Exemple : une foreuse prend du minerai de fer.")
ajouter_description_onglet(tab_pwr, "Ici, tu choisis les machines qui font de l'électricité. Exemple : une centrale brûle du carburant pour allumer les machines.")
ajouter_description_onglet(tab_auto, "L'appli regarde ce qui manque et peut t'aider à ajouter des machines. Exemple : s'il manque du fer, elle propose une foreuse.")
ajouter_description_onglet(tab_ds, "Ici, tu prépares des serveurs pour garder et envoyer des objets. Exemple : les serveurs prennent de la place dans la baie.")
ajouter_description_onglet(tab_mods, "Ici, tu changes les règles du jeu ou ajoutes des machines. Exemple : tu peux changer la vitesse d'une machine.")
ajouter_description_onglet(tab_recettes, "Ici, tu regardes comment fabriquer les objets et combien de matériaux préparer pour bâtir ton usine.")
ajouter_description_onglet(tab_wiki, "Ici, tu peux lire le petit manuel du jeu. Exemple : cherche une page pour comprendre les serveurs.")
for tab_mode in (tab_prod, tab_ext):
    bar_mode = ctk.CTkFrame(tab_mode, fg_color=THEME["bg_panel"])
    bar_mode.pack(fill="x", padx=8, pady=(2, 0))
    ctk.CTkLabel(bar_mode, text="Affichage :", text_color=THEME["text_main"]).pack(side="left", padx=(4, 6), pady=4)
    ctk.CTkSegmentedButton(
        bar_mode, values=["Ligne", "Cartes"], variable=mode_affichage_cartes,
        fg_color=THEME["bg_card_alt"], selected_color=THEME["tab_sel"],
        text_color="#FFFFFF", command=changer_mode_affichage
    ).pack(side="left", padx=4, pady=4)

# -> Onglet 1 : Ateliers
scroll_ateliers = FrameDefilantOptimise(tab_prod, fg_color=THEME["bg_panel"])
scroll_ateliers.pack(fill="both", expand=True, padx=4, pady=(4, 8))
def ajouter_carte_atelier_ui():
    c = CarteAtelierModulaire(scroll_ateliers, len(cartes_ateliers) + 1)
    cartes_ateliers.append(c)
    organiser_cartes_grille(cartes_ateliers, scroll_ateliers)
    declencher_calcul()
btn_add_atelier_main = ctk.CTkButton(tab_prod, text="+ AJOUTER UNE CARTE D'ATELIER DANS CETTE USINE", height=40, corner_radius=10, fg_color=THEME["tab_sel"], hover_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=13, weight="bold"), command=ajouter_carte_atelier_ui)
btn_add_atelier_main.pack(fill="x", padx=8, pady=(0, 6))
# -> Onglet 2 : Foreuses
scroll_foreuses = FrameDefilantOptimise(tab_ext, fg_color=THEME["bg_panel"])
scroll_foreuses.pack(fill="both", expand=True, padx=4, pady=(4, 8))
def ajouter_carte_foreuse_ui():
    c = CarteForeuseModulaire(scroll_foreuses, len(cartes_foreuses) + 1)
    cartes_foreuses.append(c)
    organiser_cartes_grille(cartes_foreuses, scroll_foreuses)
    declencher_calcul()
btn_add_foreuse_main = ctk.CTkButton(tab_ext, text="+ AJOUTER UNE FOREUSE / EXTRACTEUR DANS CETTE USINE", height=40, corner_radius=10, fg_color=THEME["seg_sel"], hover_color=THEME["tab_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=13, weight="bold"), command=ajouter_carte_foreuse_ui)
btn_add_foreuse_main.pack(fill="x", padx=8, pady=(0, 6))
# -> Onglet 3 : Parcs Énergétiques & Refined Power
scroll_parcs_energie = FrameDefilantOptimise(tab_pwr, fg_color=THEME["bg_panel"])
scroll_parcs_energie.pack(fill="both", expand=True, padx=4, pady=(4, 8))
bar_btns_pwr = ctk.CTkFrame(tab_pwr, fg_color=THEME["bg_panel"])
bar_btns_pwr.pack(fill="x", padx=8, pady=(0, 6))
def ajouter_carte_parc_ui():
    c = CarteParcEnergetique(scroll_parcs_energie, len(cartes_parcs_energie) + 1)
    c.pack(fill="x", padx=8, pady=8)
    cartes_parcs_energie.append(c)
    declencher_calcul()
def ajouter_carte_rp_ui():
    c = CarteRefinedPower(scroll_parcs_energie, len(cartes_refined_power) + 1)
    c.pack(fill="x", padx=8, pady=8)
    cartes_refined_power.append(c)
    declencher_calcul()
btn_add_parc_main = ctk.CTkButton(bar_btns_pwr, text="+ AJOUTER UN PARC ÉNERGÉTIQUE STANDARD (AVEC CHOIX DES RAFFINERIES / EXTRACTEURS)", height=40, corner_radius=10, fg_color="#065F46", hover_color="#047857", text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=ajouter_carte_parc_ui)
btn_add_parc_main.pack(side="left", expand=True, fill="x", padx=(0, 4))
btn_add_rp_main = ctk.CTkButton(bar_btns_pwr, text="+ AJOUTER UNE CHAÎNE REFINED POWER (CHAUDIÈRE VAPEUR ➔ TURBINE RPM ➔ ALTERNATEUR MW)", height=40, corner_radius=10, fg_color=THEME["accent_purple"], hover_color="#5B21B6", text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=ajouter_carte_rp_ui)
btn_add_rp_main.pack(side="right", expand=True, fill="x", padx=(4, 0))
# ==============================================================================
# 12. ONGLET 5 : DIGITAL STORAGE (RÉSEAU INFORMATIQUE D'OBJETS INTER-USINES)
# ==============================================================================
scroll_ds = FrameDefilantOptimise(tab_ds, fg_color=THEME["bg_panel"])
scroll_ds.pack(fill="both", expand=True, padx=6, pady=6)
card_ds_info = ctk.CTkFrame(scroll_ds, fg_color=THEME["bg_card"], border_color=THEME["tab_sel"], border_width=2, corner_radius=12)
card_ds_info.pack(fill="x", padx=8, pady=6)
lbl_bilan_ds_header = ctk.CTkLabel(card_ds_info, text="🌐 RÉSEAU DIGITAL STORAGE", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color=THEME["text_main"])
lbl_bilan_ds_header.pack(anchor="w", padx=14, pady=(10, 4))
lbl_cloud_global_ds = ctk.CTkLabel(card_ds_info, text="☁️ État du Stockage Cloud Inter-Usines : Équilibré", font=ctk.CTkFont(family="Consolas", size=12), text_color=THEME["status_ok"])
lbl_cloud_global_ds.pack(anchor="w", padx=14, pady=(0, 10))
# Infrastructure matérielle Digital Storage
card_ds_hw = ctk.CTkFrame(scroll_ds, fg_color=THEME["bg_card"], border_color=THEME["border"], border_width=1, corner_radius=12)
card_ds_hw.pack(fill="x", padx=8, pady=6)
hdr_ds_hw = ctk.CTkFrame(card_ds_hw, fg_color=THEME["bg_card"])
hdr_ds_hw.pack(fill="x", padx=14, pady=(10, 4))
ctk.CTkLabel(hdr_ds_hw, text="🖥️ A. INFRASTRUCTURE MATÉRIELLE DU RÉSEAU (SERVEURS, BAIES DE DISQUES, TERMINAUX, BUS)", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"]).pack(side="left")
def ajouter_ds_equip_ui():
    c = CarteEquipementDigitalStorage(frame_ds_equip_list)
    c.pack(fill="x", padx=8, pady=4)
    cartes_ds_equip.append(c)
    declencher_calcul()
ctk.CTkButton(hdr_ds_hw, text="+ Ajouter Équipement Réseau", corner_radius=8, fg_color=THEME["tab_sel"], text_color="#FFFFFF", command=ajouter_ds_equip_ui).pack(side="right")
frame_ds_equip_list = ctk.CTkFrame(card_ds_hw, fg_color=THEME["bg_card"])
frame_ds_equip_list.pack(fill="x", padx=6, pady=(4, 10))
# Flux Cloud Upload / Download
card_ds_cloud = ctk.CTkFrame(scroll_ds, fg_color=THEME["bg_card"], border_color=THEME["border"], border_width=1, corner_radius=12)
card_ds_cloud.pack(fill="x", padx=8, pady=6)
hdr_ds_cl = ctk.CTkFrame(card_ds_cloud, fg_color=THEME["bg_card"])
hdr_ds_cl.pack(fill="x", padx=14, pady=(10, 4))
ctk.CTkLabel(hdr_ds_cl, text="☁️ B. FLUX DE TRANSFERT CLOUD INTER-USINES (UPLOAD / DOWNLOAD D'OBJETS SUR LE RÉSEAU)", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"]).pack(side="left")
def ajouter_ds_flux_ui():
    c = CarteFluxDigitalStorage(frame_ds_flux_list)
    c.pack(fill="x", padx=8, pady=4)
    cartes_ds_flux.append(c)
    declencher_calcul()
ctk.CTkButton(hdr_ds_cl, text="+ Ajouter un Flux Upload / Download", corner_radius=8, fg_color="#065F46", text_color="#FFFFFF", command=ajouter_ds_flux_ui).pack(side="right")
frame_ds_flux_list = ctk.CTkFrame(card_ds_cloud, fg_color=THEME["bg_card"])
frame_ds_flux_list.pack(fill="x", padx=6, pady=(4, 10))
# ==============================================================================
# 13. ONGLET 4 : AUTO-SOLVEUR DE DÉFICITS (MATÉRIAUX + ÉNERGIE) & GÉNÉRATEUR D'USINE
# ==============================================================================
scroll_auto = FrameDefilantOptimise(tab_auto, fg_color=THEME["bg_panel"])
scroll_auto.pack(fill="both", expand=True, padx=6, pady=6)
def ajouter_ou_fusionner_atelier_dans_usine(nom_usine_cible, machine, type_rec, nom_recette, qte_ajout, cad_str, somers_str="0"):
    u_cible = usines_data[nom_usine_cible]
    for a_ex in u_cible["ateliers"]:
        if a_ex.get("recette") == nom_recette and str(a_ex.get("cadence")) == str(cad_str) and str(a_ex.get("somers", "0")) == str(somers_str):
            try:
                a_ex["qte"] = str(int(a_ex.get("qte", "0")) + int(qte_ajout))
                return
            except ValueError:
                pass
    u_cible["ateliers"].append({"machine": machine, "type": type_rec, "recette": nom_recette, "qte": str(qte_ajout), "cadence": str(cad_str), "somers": str(somers_str)})
def ajouter_ou_fusionner_foreuse_dans_usine(nom_usine_cible, machine, tier, purete, ressource, qte_ajout, cad_str):
    u_cible = usines_data[nom_usine_cible]
    for f_ex in u_cible["foreuses"]:
        if f_ex.get("machine") == machine and f_ex.get("ressource") == ressource and f_ex.get("tier") == tier and f_ex.get("purete") == purete and str(f_ex.get("cadence")) == str(cad_str):
            try:
                f_ex["qte"] = str(int(f_ex.get("qte", "0")) + int(qte_ajout))
                return
            except ValueError:
                pass
    u_cible["foreuses"].append({"machine": machine, "tier": tier, "purete": purete, "ressource": ressource, "qte": str(qte_ajout), "cadence": str(cad_str), "somers": "0"})
def appliquer_resolution_deficit_electrique(deficit_mw, filiere_choisie, cad_str, recharger_ui=True):
    synchroniser_usine_active()
    if deficit_mw <= 0.05:
        return
    try:
        cad_pct = max(float(str(cad_str).replace("%", "")), 1.0)
    except ValueError:
        cad_pct = 100.0
    cad_clean = str(int(cad_pct))
    spec = FILIERES_ENERGIE.get(filiere_choisie, list(FILIERES_ENERGIE.values())[0])
    cad_etapes = {et["id"]: cad_clean for et in spec["etapes"]}
    portee_ressources = "Usine Active" if portee_bilan_var.get() == "🏭 Usine Active" else "Réseau Global"
    flux_courant = dernier_flux_calcule_usine if portee_ressources == "Usine Active" else dernier_flux_calcule_global
    flux_disponibles = {item: max(qte, 0.0) for item, qte in flux_courant.items()}
    cfg_sim = {"filiere": filiere_choisie, "mode": "Auto-Compensation Déficit", "portee_auto": portee_ressources, "nb_fixe": "1", "cadence_gen": cad_clean, "boucle_auto": True, "actif": True, "cadences_etapes": cad_etapes, "qtes_etapes": {}}
    res_sim = simuler_parc_energetique(cfg_sim, deficit_mw, flux_disponibles)
    nb_gen_ajout = max(int(res_sim["nb_gen"]), 1)
    u_cible = usines_data[usine_active_nom]
    parc_trouve = False
    for p_ex in u_cible["parcs_energie"]:
        if p_ex.get("actif", True) and p_ex.get("mode") == "Parc Fixe (Existant)" and p_ex.get("filiere") == filiere_choisie and str(p_ex.get("cadence_gen")) == cad_clean and p_ex.get("portee_auto", "Réseau Global") == portee_ressources:
            try:
                p_ex["nb_fixe"] = str(int(p_ex.get("nb_fixe", "0")) + nb_gen_ajout)
                parc_trouve = True
                break
            except ValueError:
                pass
    if not parc_trouve:
        u_cible["parcs_energie"].append({"filiere": filiere_choisie, "mode": "Parc Fixe (Existant)", "portee_auto": portee_ressources, "nb_fixe": str(nb_gen_ajout), "cadence_gen": cad_clean, "boucle_auto": True, "actif": True, "cadences_etapes": cad_etapes, "qtes_etapes": {}})
    if recharger_ui:
        charger_usine_dans_ui(usine_active_nom)
def appliquer_option_resolution_deficit(objet, debit_manquant, option_choisie, cad_str, somers_str="0"):
    synchroniser_usine_active()
    try:
        cad_pct = max(float(cad_str.replace("%", "")), 1.0)
    except ValueError:
        cad_pct = 100.0
    cad = cad_pct / 100.0
    if option_choisie.startswith("[EXTRACTION]"):
        if "Foreuse" in option_choisie:
            tier = "Mk.3" if "Mk.3" in option_choisie else ("Mk.1" if "Mk.1" in option_choisie else "Mk.2")
            nb_req = max(math.ceil(debit_manquant / (PROD_FOREUSE_BASE[tier] * cad)), 1)
            res_nom = "Uranium" if objet == "Minerai d'uranium" else objet
            ajouter_ou_fusionner_foreuse_dans_usine(usine_active_nom, "Foreuse", tier, "Normal (1.0x)", res_nom, nb_req, str(int(cad_pct)))
        elif "Pompe à eau" in option_choisie:
            nb_req = max(math.ceil(debit_manquant / (120.0 * cad)), 1)
            ajouter_ou_fusionner_foreuse_dans_usine(usine_active_nom, "Pompe à eau", "Mk.1", "Normal (1.0x)", "Eau", nb_req, str(int(cad_pct)))
        else:
            nb_req = max(math.ceil(debit_manquant / (120.0 * cad)), 1)
            ajouter_ou_fusionner_foreuse_dans_usine(usine_active_nom, "Extracteur de pétrole", "Mk.1", "Normal (1.0x)", "Pétrole brut", nb_req, str(int(cad_pct)))
    else:
        fin_cro = option_choisie.find("] ")
        if fin_cro == -1:
            return
        nom_rec = option_choisie[fin_cro + 2:]
        m_rec = df[df['Nom de la recette'] == nom_rec]
        if m_rec.empty:
            return
        rec = m_rec.iloc[0]
        bat = rec['Bâtiment']
        type_r = "Alternative" if rec['Est Alternative'] else "Standard"
        s_max = int(get_machine_specs(bat).get("somers_max", 1))
        s_used = min(int(somers_str) if str(somers_str).isdigit() else 0, s_max)
        prod_mult, _ = calculer_multiplicateurs_somers(s_used, s_max)
        vit_mod = float(get_machine_specs(bat).get("vitesse", 1.0))
        out_base = max(float(rec['Sortie 1 / Min']) if rec.get('Sortie 1') == objet else float(rec.get('Sortie 2 / Min', 1.0)), 0.1)
        nb_req = max(math.ceil(debit_manquant / (out_base * vit_mod * cad * prod_mult)), 1)
        ajouter_ou_fusionner_atelier_dans_usine(usine_active_nom, bat, type_r, nom_rec, nb_req, str(int(cad_pct)), str(s_used))
    charger_usine_dans_ui(usine_active_nom)
def lister_options_pour_objet(objet):
    options = []
    if objet in RESSOURCES_EXTRACTION_MAP:
        t_ext = RESSOURCES_EXTRACTION_MAP[objet]
        if t_ext == "Foreuse":
            options.extend([f"[EXTRACTION] Foreuse Mk.2 (Normal) ➔ {objet}", f"[EXTRACTION] Foreuse Mk.3 (Normal) ➔ {objet}", f"[EXTRACTION] Foreuse Mk.1 (Normal) ➔ {objet}"])
        elif t_ext == "Pompe à eau":
            options.append("[EXTRACTION] Pompe à eau ➔ Eau")
        else:
            options.append("[EXTRACTION] Extracteur de pétrole (Normal) ➔ Pétrole brut")
    recs = df[(df['Sortie 1'] == objet) | (df['Sortie 2'] == objet)]
    for _, r in pd.concat([recs[~recs['Est Alternative']], recs[recs['Est Alternative']]]).iterrows():
        options.append(f"[{r['Bâtiment']}] {r['Nom de la recette']}")
    return options if options else ["Aucune méthode trouvée"]
def trouver_recette_optimale(objet, pref_dict=None):
    if pref_dict and objet in pref_dict:
        m = df[df['Nom de la recette'] == pref_dict[objet]]
        if not m.empty:
            return m.iloc[0]
    cand = df[(df['Sortie 1'] == objet) & (~df['Est Alternative']) & (~df['Nom de la recette'].str.contains('Déconditionnement', case=False, na=False))]
    if not cand.empty:
        return cand.iloc[0]
    cand_all = df[df['Sortie 1'] == objet]
    return cand_all.iloc[0] if not cand_all.empty else None
def calculer_arbre_top_down(objet_cible, debit_cible, pref_dict=None):
    besoins_restants = {objet_cible: float(debit_cible)}
    recettes_agregees, extractions_agregees, visites = {}, {}, {}
    for _ in range(35):
        items_a_traiter = [it for it, val in list(besoins_restants.items()) if val > 0.001 and it not in RESSOURCES_EXTRACTION_MAP]
        if not items_a_traiter:
            break
        for it in items_a_traiter:
            qte_req = besoins_restants.pop(it)
            visites[it] = visites.get(it, 0) + 1
            if visites[it] > 12:
                extractions_agregees[it] = extractions_agregees.get(it, 0.0) + qte_req
                continue
            rec = trouver_recette_optimale(it, pref_dict)
            if rec is None or float(rec['Sortie 1 / Min']) <= 0:
                extractions_agregees[it] = extractions_agregees.get(it, 0.0) + qte_req
                continue
            nom_r = rec['Nom de la recette']
            recettes_agregees[nom_r] = recettes_agregees.get(nom_r, 0.0) + qte_req
            ratio_cycles = qte_req / float(rec['Sortie 1 / Min'])
            for i in range(1, 5):
                in_nom, in_val = rec.get(f'Entrée {i}'), rec.get(f'Entrée {i} / Min')
                if pd.notna(in_nom) and pd.notna(in_val) and float(in_val) > 0:
                    besoins_restants[in_nom] = besoins_restants.get(in_nom, 0.0) + (float(in_val) * ratio_cycles)
    for it, val in besoins_restants.items():
        if val > 0.001:
            extractions_agregees[it] = extractions_agregees.get(it, 0.0) + val
    return recettes_agregees, extractions_agregees
frame_liste_deficits_dyn = None
seg_cad_deficits_global = None
menu_filiere_def_elec_global = None
def resoudre_tous_les_deficits_en_cascade():
    synchroniser_usine_active()
    cad_str = seg_cad_deficits_global.get().replace("%", "") if seg_cad_deficits_global else "100"
    filiere_elec = menu_filiere_def_elec_global.get() if menu_filiere_def_elec_global else "💧 Centrale au Carburant Dilué (Optimisé - 250 MW)"
    for _ in range(3):
        for _ in range(25):
            flux_courant = dernier_flux_calcule_usine if portee_bilan_var.get() == "🏭 Usine Active" else dernier_flux_calcule_global
            deficits = [(it, abs(val)) for it, val in flux_courant.items() if val < -0.05]
            if not deficits:
                break
            for it, manque in deficits:
                opts = lister_options_pour_objet(it)
                if opts and opts[0] != "Aucune méthode trouvée":
                    appliquer_option_resolution_deficit(it, manque, opts[0], cad_str, "0")
        def_mw = dernier_deficit_mw_usine if portee_bilan_var.get() == "🏭 Usine Active" else dernier_deficit_mw_global
        if def_mw > 0.05:
            appliquer_resolution_deficit_electrique(def_mw, filiere_elec, cad_str, recharger_ui=True)
        else:
            break
    popup_success("Résolution Terminée", "Tous les déficits matériels et énergétiques ont été comblés !")
def rafraichir_liste_deficits_ui():
    if frame_liste_deficits_dyn is None or not frame_liste_deficits_dyn.winfo_exists():
        return
    for w in frame_liste_deficits_dyn.winfo_children():
        w.destroy()
    flux_source = dernier_flux_calcule_usine if portee_bilan_var.get() == "🏭 Usine Active" else dernier_flux_calcule_global
    def_mw = dernier_deficit_mw_usine if portee_bilan_var.get() == "🏭 Usine Active" else dernier_deficit_mw_global
    deficits = [(it, abs(val)) for it, val in sorted(flux_source.items()) if val < -0.05]
    cad_defaut = seg_cad_deficits_global.get().replace("%", "") if seg_cad_deficits_global else "100"
    fil_defaut = menu_filiere_def_elec_global.get() if menu_filiere_def_elec_global else "💧 Centrale au Carburant Dilué (Optimisé - 250 MW)"
    if def_mw <= 0.05 and not deficits:
        ctk.CTkLabel(frame_liste_deficits_dyn, text="✅ Aucun déficit matériel ni énergétique !", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["status_ok"]).pack(anchor="w", padx=12, pady=10)
        return
    if def_mw > 0.05:
        row_e = ctk.CTkFrame(frame_liste_deficits_dyn, fg_color=THEME["bg_card_alt"], border_color=THEME["status_warn"], border_width=2, corner_radius=8)
        row_e.pack(fill="x", padx=8, pady=(6, 8))
        ctk.CTkLabel(row_e, text=f"⚡ DÉFICIT ÉNERGÉTIQUE (Manque : {def_mw:.1f} MW)", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=THEME["status_warn"], width=285, anchor="w").pack(side="left", padx=(10, 6), pady=10)
        menu_fil_row = ctk.CTkOptionMenu(row_e, values=list(FILIERES_ENERGIE.keys()), width=325, fg_color=THEME["bg_card"], button_color=THEME["tab_sel"], text_color=THEME["text_main"])
        menu_fil_row.pack(side="left", padx=6, pady=10)
        menu_fil_row.set(fil_defaut)
        ent_cad_e = ctk.CTkEntry(row_e, width=55, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        ent_cad_e.pack(side="left", padx=4, pady=10)
        ent_cad_e.insert(0, cad_defaut)
        ctk.CTkButton(row_e, text="⚡ Combler Déficit MW", width=165, height=30, corner_radius=8, fg_color="#B45309", text_color="#FFFFFF", command=lambda mw_m=def_mw, mf=menu_fil_row, ec=ent_cad_e: appliquer_resolution_deficit_electrique(mw_m, mf.get(), ec.get().strip(), True)).pack(side="right", padx=10, pady=10)
    for it_nom, val_manque in deficits:
        row_d = ctk.CTkFrame(frame_liste_deficits_dyn, fg_color=THEME["bg_card_alt"], border_color=THEME["border"], border_width=1, corner_radius=8)
        row_d.pack(fill="x", padx=8, pady=4)
        ctk.CTkLabel(row_d, text=f"🔴 {it_nom} (Manque : {val_manque:.1f} / min)", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=THEME["status_err"], width=285, anchor="w").pack(side="left", padx=(10, 6), pady=8)
        opts = lister_options_pour_objet(it_nom)
        menu_opt = ctk.CTkOptionMenu(row_d, values=opts, width=325, fg_color=THEME["bg_card"], button_color=THEME["tab_sel"], text_color=THEME["text_main"])
        menu_opt.pack(side="left", padx=6, pady=8)
        menu_opt.set(opts[0])
        ent_cad_d = ctk.CTkEntry(row_d, width=55, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        ent_cad_d.pack(side="left", padx=4, pady=8)
        ent_cad_d.insert(0, cad_defaut)
        ctk.CTkButton(row_d, text="➕ Combler ce déficit", width=165, height=30, corner_radius=8, fg_color="#065F46", text_color="#FFFFFF", command=lambda in_n=it_nom, mq=val_manque, mo=menu_opt, ec=ent_cad_d: appliquer_option_resolution_deficit(in_n, mq, mo.get(), ec.get().strip(), "0")).pack(side="right", padx=10, pady=8)
def construire_onglet_auto():
    global frame_liste_deficits_dyn, seg_cad_deficits_global, menu_filiere_def_elec_global
    for w in scroll_auto.winfo_children():
        w.destroy()
    paliers = generer_paliers_cadence()
    card_def = ctk.CTkFrame(scroll_auto, fg_color=THEME["bg_card"], border_color=THEME["tab_sel"], border_width=2, corner_radius=12)
    card_def.pack(fill="x", padx=8, pady=(6, 12))
    hdr_def = ctk.CTkFrame(card_def, fg_color=THEME["bg_card"])
    hdr_def.pack(fill="x", padx=14, pady=(12, 6))
    ctk.CTkLabel(hdr_def, text="⚡ OUTIL 1 : RÉSOLVEUR DE DÉFICITS MATÉRIELS & ÉNERGÉTIQUES", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["text_main"]).pack(side="left")
    ctk.CTkButton(hdr_def, text="🚀 TOUT RÉSOUDRE EN CASCADE (MATÉRIAUX + ÉNERGIE)", height=32, corner_radius=8, fg_color=THEME["tab_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=resoudre_tous_les_deficits_en_cascade).pack(side="right")
    bar_cad_def = ctk.CTkFrame(card_def, fg_color=THEME["bg_card_alt"], corner_radius=8)
    bar_cad_def.pack(fill="x", padx=14, pady=4)
    ctk.CTkLabel(bar_cad_def, text="Cadence :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(10, 6), pady=8)
    seg_cad_deficits_global = ctk.CTkSegmentedButton(bar_cad_def, values=paliers, fg_color=THEME["bg_panel"], selected_color=THEME["seg_sel"], text_color="#FFFFFF", command=lambda _: rafraichir_liste_deficits_ui())
    seg_cad_deficits_global.set("100%")
    seg_cad_deficits_global.pack(side="left", padx=4, pady=8)
    ctk.CTkLabel(bar_cad_def, text="Filière Élec. :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(14, 6), pady=8)
    menu_filiere_def_elec_global = ctk.CTkOptionMenu(bar_cad_def, values=list(FILIERES_ENERGIE.keys()), width=270, fg_color=THEME["bg_card"], button_color=THEME["tab_sel"], text_color=THEME["text_main"], command=lambda _: rafraichir_liste_deficits_ui())
    menu_filiere_def_elec_global.pack(side="left", padx=4, pady=8)
    menu_filiere_def_elec_global.set("💧 Centrale au Carburant Dilué (Optimisé - 250 MW)")
    frame_liste_deficits_dyn = ctk.CTkFrame(card_def, fg_color=THEME["bg_card"])
    frame_liste_deficits_dyn.pack(fill="x", padx=6, pady=(4, 12))
    # Générateur d'Usine sur Objectif
    card_gen = ctk.CTkFrame(scroll_auto, fg_color=THEME["bg_card"], border_color=THEME["seg_sel"], border_width=2, corner_radius=12)
    card_gen.pack(fill="x", padx=8, pady=8)
    ctk.CTkLabel(card_gen, text="🎯 OUTIL 2 : GÉNÉRATEUR AUTOMATIQUE D'USINE SUR OBJECTIF (DE A à Z)", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=14, pady=(12, 6))
    r_g1 = ctk.CTkFrame(card_gen, fg_color=THEME["bg_card_alt"], corner_radius=8)
    r_g1.pack(fill="x", padx=14, pady=4)
    ctk.CTkLabel(r_g1, text="Produit Cible :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(10, 4), pady=10)
    combo_cible_obj = ctk.CTkComboBox(r_g1, values=liste_objets_produits, width=250, fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    combo_cible_obj.pack(side="left", padx=6)
    combo_cible_obj.set("Cadre modulaire lourd" if "Cadre modulaire lourd" in liste_objets_produits else liste_objets_produits[0])
    ctk.CTkLabel(r_g1, text="Débit (/min) :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
    ent_cible_debit = ctk.CTkEntry(r_g1, width=65, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    ent_cible_debit.pack(side="left", padx=4)
    ent_cible_debit.insert(0, "10")
    seg_dest_gen = ctk.CTkSegmentedButton(r_g1, values=["Créer Nouvelle Usine dédiée", "Ajouter dans l'Usine Active"], fg_color=THEME["bg_panel"], selected_color=THEME["tab_sel"], text_color="#FFFFFF")
    seg_dest_gen.set("Créer Nouvelle Usine dédiée")
    seg_dest_gen.pack(side="left", padx=10, pady=10)
    lbl_preview_auto = ctk.CTkLabel(card_gen, text="Cliquez sur Prévisualiser ou Générer...", justify="left", anchor="w", font=ctk.CTkFont(family="Consolas", size=12), fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"], corner_radius=8, padx=12, pady=10)
    lbl_preview_auto.pack(fill="x", padx=14, pady=6)
    def previsualiser_usine_auto():
        obj_c = combo_cible_obj.get().strip()
        try:
            deb_c = float(ent_cible_debit.get().strip().replace(",", "."))
        except ValueError:
            return
        rec_ag, ext_ag = calculer_arbre_top_down(obj_c, deb_c, preferences_recettes_auto)
        lignes_p = [f"📋 PLAN D'USINE POUR : {deb_c:.1f}x {obj_c} / min\n🏭 ATELIERS REQUIS :"]
        for r_nom, q_tot in rec_ag.items():
            rec_row = df[df['Nom de la recette'] == r_nom].iloc[0]
            bat = rec_row['Bâtiment']
            nb_m = math.ceil(q_tot / (float(rec_row['Sortie 1 / Min']) * float(get_machine_specs(bat).get("vitesse", 1.0))))
            lignes_p.append(f"   • {nb_m:3d}x {bat:<20} │ {r_nom:<36} │ {q_tot:.1f} /min")
        lignes_p.append("\n⛏️ EXTRACTEURS REQUIS (Foreuses Mk.2 Normal) :")
        for res_n, q_ext in ext_ag.items():
            nb_e = math.ceil(q_ext / 120.0)
            lignes_p.append(f"   • {nb_e:3d}x Extracteur ({res_n:<20}) │ {q_ext:.1f} /min")
        lbl_preview_auto.configure(text="\n".join(lignes_p))
    def executer_generation_usine_auto():
        synchroniser_usine_active()
        obj_c = combo_cible_obj.get().strip()
        try:
            deb_c = float(ent_cible_debit.get().strip().replace(",", "."))
        except ValueError:
            popup_error("Erreur", "Débit invalide.")
            return
        rec_ag, ext_ag = calculer_arbre_top_down(obj_c, deb_c, preferences_recettes_auto)
        if seg_dest_gen.get() == "Créer Nouvelle Usine dédiée":
            nom_cible = f"Usine {obj_c} ({deb_c:g}_min)"
            cpt = 2
            while nom_cible in usines_data:
                nom_cible = f"Usine {obj_c} #{cpt}"
                cpt += 1
            usines_data[nom_cible] = creer_structure_usine_vide()
        else:
            nom_cible = usine_active_nom
        for r_nom, q_tot in rec_ag.items():
            rec_row = df[df['Nom de la recette'] == r_nom].iloc[0]
            bat = rec_row['Bâtiment']
            type_r = "Alternative" if rec_row['Est Alternative'] else "Standard"
            nb_m = max(math.ceil(q_tot / (float(rec_row['Sortie 1 / Min']) * float(get_machine_specs(bat).get("vitesse", 1.0)))), 1)
            ajouter_ou_fusionner_atelier_dans_usine(nom_cible, bat, type_r, r_nom, nb_m, "100", "0")
        for res_n, q_ext in ext_ag.items():
            t_ext = RESSOURCES_EXTRACTION_MAP.get(res_n, "Foreuse")
            nb_e = max(math.ceil(q_ext / 120.0), 1)
            res_clean = "Uranium" if res_n == "Minerai d'uranium" else res_n
            ajouter_ou_fusionner_foreuse_dans_usine(nom_cible, t_ext, "Mk.2", "Normal (1.0x)", res_clean, nb_e, "100")
        sauvegarder_usine_dans_son_dossier(nom_cible, usines_data[nom_cible])
        menu_usine_active.configure(values=list(usines_data.keys()))
        menu_usine_active.set(nom_cible)
        charger_usine_dans_ui(nom_cible)
        tabs.set("🏭 1. ATELIERS")
        popup_success("Usine Générée !", f"L'usine '{nom_cible}' et son dossier dans Documents ont été générés !")
    bar_b = ctk.CTkFrame(card_gen, fg_color=THEME["bg_card"])
    bar_b.pack(fill="x", padx=14, pady=(4, 12))
    ctk.CTkButton(bar_b, text="🔍 PRÉVISUALISER L'ARBRE", height=38, corner_radius=10, fg_color=THEME["seg_sel"], text_color="#FFFFFF", command=previsualiser_usine_auto).pack(side="left", expand=True, fill="x", padx=(0, 6))
    ctk.CTkButton(bar_b, text="🚀 GÉNÉRER L'USINE COMPLÈTE", height=38, corner_radius=10, fg_color="#065F46", text_color="#FFFFFF", command=executer_generation_usine_auto).pack(side="right", expand=True, fill="x", padx=(6, 0))
    previsualiser_usine_auto()
    rafraichir_liste_deficits_ui()
# ==============================================================================
# 14. ONGLET 6 : LABORATOIRE DE MODS (AVEC CHOIX DU TYPE DE MACHINE & SUPPRESSION)
# ==============================================================================
scroll_mods = FrameDefilantOptimise(tab_mods, fg_color=THEME["bg_panel"])
scroll_mods.pack(fill="both", expand=True, padx=6, pady=6)
def reinitialiser_tous_les_mods():
    if not popup_askyesno("Réinitialisation Complète", "Supprimer toutes les machines/recettes moddées et restaurer les valeurs Vanilla ?"):
        return
    MODS_CONFIG.update(LOIS_VANILLA)
    MODS_CONFIG["machines_custom"] = {k: dict(v) for k, v in MACHINES_VANILLA.items()}
    MODS_CONFIG["recettes_custom"] = []
    sauvegarder_mods()
    charger_et_fusionner_donnees()
    synchroniser_usine_active()
    charger_usine_dans_ui(usine_active_nom)
    construire_onglet_mods()
    construire_onglet_auto()
    popup_success("Retour Vanilla", "Tous les mods ont été réinitialisés.")
def supprimer_ou_restaurer_machine_specifique(nom_m):
    if not nom_m or nom_m not in MODS_CONFIG["machines_custom"]:
        return
    synchroniser_usine_active()
    if nom_m in MACHINES_VANILLA:
        MODS_CONFIG["machines_custom"][nom_m] = dict(MACHINES_VANILLA[nom_m])
        msg = f"La machine '{nom_m}' a été restaurée à ses valeurs d'origine."
    else:
        if not popup_askyesno("Supprimer Machine", f"Supprimer définitivement la machine '{nom_m}' ?"):
            return
        MODS_CONFIG["machines_custom"].pop(nom_m, None)
        msg = f"La machine '{nom_m}' a été supprimée."
    sauvegarder_mods()
    charger_et_fusionner_donnees()
    charger_usine_dans_ui(usine_active_nom)
    construire_onglet_mods()
    construire_onglet_auto()
    popup_success("Machine mise à jour", msg)
def construire_onglet_mods():
    for w in scroll_mods.winfo_children():
        w.destroy()
    top_mods_bar = ctk.CTkFrame(scroll_mods, fg_color=THEME["bg_card"], border_color=THEME["border"], border_width=1, corner_radius=10)
    top_mods_bar.pack(fill="x", padx=8, pady=(4, 8))
    ctk.CTkLabel(top_mods_bar, text="🧬 LABORATOIRE DE MODS (LOIS PHYSIQUES, TYPES DE MACHINES, REFINED POWER & RECETTES)", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=14, pady=10)
    ctk.CTkButton(top_mods_bar, text="⚠️ RÉINITIALISER TOUS LES MODS", corner_radius=8, fg_color="#991B1B", text_color="#FFFFFF", command=reinitialiser_tous_les_mods).pack(side="right", padx=14, pady=10)
    # Panneau A : Lois Physiques
    card_mods_phys = ctk.CTkFrame(scroll_mods, fg_color=THEME["bg_card"], border_color=THEME["border"], border_width=1, corner_radius=10)
    card_mods_phys.pack(fill="x", padx=8, pady=6)
    ctk.CTkLabel(card_mods_phys, text="⚡ A. SURCADENÇAGE SYNTHÉTIQUE (x500+) & SOMERSLOOPS SYNTHÉTIQUES", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=14, pady=(10, 4))
    grid_phys = ctk.CTkFrame(card_mods_phys, fg_color=THEME["bg_card_alt"], corner_radius=8)
    grid_phys.pack(fill="x", padx=14, pady=6)
    def creer_champ_mod_phys(row, col, label_txt, val_defaut):
        ctk.CTkLabel(grid_phys, text=label_txt, font=ctk.CTkFont(size=12), text_color=THEME["text_main"]).grid(row=row, column=col*2, padx=(10, 4), pady=6, sticky="w")
        ent = ctk.CTkEntry(grid_phys, width=75, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
        ent.grid(row=row, column=col*2 + 1, padx=(0, 14), pady=6, sticky="w")
        ent.insert(0, str(val_defaut))
        return ent
    ent_mod_max_cad = creer_champ_mod_phys(0, 0, "Cadence Max (%) [250, 500, 1000] :", MODS_CONFIG["max_cadence_pct"])
    ent_mod_gain_sh = creer_champ_mod_phys(0, 1, "Gain / Éclat (%) [Vanilla=50] :", MODS_CONFIG["gain_par_eclat_pct"])
    ent_mod_exp_surc = creer_champ_mod_phys(0, 2, "Exposant Élec. Surc. [1.6] :", MODS_CONFIG["exposant_surcadencage"])
    ent_mod_bonus_som = creer_champ_mod_phys(1, 0, "Bonus Prod Somers. (%) [100] :", MODS_CONFIG["bonus_prod_somersloop_pct"])
    ent_mod_exp_som = creer_champ_mod_phys(1, 1, "Exposant Élec. Somers. [2.0] :", MODS_CONFIG["exposant_elec_somersloop"])
    def appliquer_lois_moddees():
        try:
            MODS_CONFIG["max_cadence_pct"] = int(float(ent_mod_max_cad.get().strip()))
            MODS_CONFIG["gain_par_eclat_pct"] = float(ent_mod_gain_sh.get().strip())
            MODS_CONFIG["exposant_surcadencage"] = float(ent_mod_exp_surc.get().strip())
            MODS_CONFIG["bonus_prod_somersloop_pct"] = float(ent_mod_bonus_som.get().strip())
            MODS_CONFIG["exposant_elec_somersloop"] = float(ent_mod_exp_som.get().strip())
            sauvegarder_mods()
            synchroniser_usine_active()
            charger_usine_dans_ui(usine_active_nom)
            construire_onglet_auto()
            popup_success("Lois Appliquées", "Paramètres physiques mis à jour !")
        except ValueError:
            popup_error("Erreur", "Nombres invalides.")
    ctk.CTkButton(card_mods_phys, text="💾 APPLIQUER CES LOIS PHYSIQUES", corner_radius=8, fg_color=THEME["tab_sel"], text_color="#FFFFFF", command=appliquer_lois_moddees).pack(anchor="e", padx=14, pady=(2, 10))
    # Panneau B : Machines Moddées avec CHOIX DU TYPE DE MACHINE
    card_mods_mach = ctk.CTkFrame(scroll_mods, fg_color=THEME["bg_card"], border_color=THEME["border"], border_width=1, corner_radius=10)
    card_mods_mach.pack(fill="x", padx=8, pady=6)
    ctk.CTkLabel(card_mods_mach, text="🏭 B. CRÉER OU MODIFIER UNE MACHINE (CHOIX DU TYPE : PRODUCTION, EXTRACTION, ÉNERGIE, REFINED POWER)", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=14, pady=(10, 4))
    row_m1 = ctk.CTkFrame(card_mods_mach, fg_color=THEME["bg_card_alt"], corner_radius=8)
    row_m1.pack(fill="x", padx=14, pady=4)
    ctk.CTkLabel(row_m1, text="Nom Machine :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4), pady=8)
    combo_mod_machine = ctk.CTkComboBox(row_m1, values=list(MODS_CONFIG["machines_custom"].keys()), width=200, fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    combo_mod_machine.pack(side="left", padx=4, pady=8)
    combo_mod_machine.set("Constructeur")
    ctk.CTkLabel(row_m1, text="Catégorie :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
    def on_cat_mod_change(cat_choisie):
        if cat_choisie in ["Énergie Directe", "Refined Power : Alternateur (RPM ➔ MW)"]:
            menu_sens_mw.set("Produit")
            lbl_mach_mw.configure(text="Production (MW) :")
        else:
            menu_sens_mw.set("Consomme")
            lbl_mach_mw.configure(text="Conso (MW) :")
    menu_mod_cat = ctk.CTkOptionMenu(row_m1, values=CATEGORIES_MACHINES, width=250, fg_color=THEME["bg_card"], button_color=THEME["tab_sel"], text_color=THEME["text_main"], command=on_cat_mod_change)
    menu_mod_cat.pack(side="left", padx=4)
    menu_mod_cat.set("Production")
    row_m2 = ctk.CTkFrame(card_mods_mach, fg_color=THEME["bg_card_alt"], corner_radius=8)
    row_m2.pack(fill="x", padx=14, pady=4)
    lbl_mach_mw = ctk.CTkLabel(row_m2, text="Conso (MW) :", text_color=THEME["text_main"])
    lbl_mach_mw.pack(side="left", padx=(10, 4), pady=8)
    ent_mach_mw = ctk.CTkEntry(row_m2, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    ent_mach_mw.pack(side="left", padx=4)
    ent_mach_mw.insert(0, "4.0")
    ctk.CTkLabel(row_m2, text="Sens électrique :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
    menu_sens_mw = ctk.CTkSegmentedButton(
        row_m2, values=["Consomme", "Produit"], width=150,
        fg_color=THEME["bg_panel"], selected_color=THEME["tab_sel"],
        text_color="#FFFFFF",
        command=lambda sens: lbl_mach_mw.configure(
            text="Production (MW) :" if sens == "Produit" else "Conso (MW) :"
        )
    )
    menu_sens_mw.set("Consomme")
    menu_sens_mw.pack(side="left", padx=4)
    ctk.CTkLabel(row_m2, text="Vitesse (x1.0...) :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
    ent_mach_vit = ctk.CTkEntry(row_m2, width=60, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    ent_mach_vit.pack(side="left", padx=4)
    ent_mach_vit.insert(0, "1.0")
    ctk.CTkLabel(row_m2, text="Slots Somers. :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
    ent_mach_som = ctk.CTkEntry(row_m2, width=50, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    ent_mach_som.pack(side="left", padx=4)
    ent_mach_som.insert(0, "1")
    ctk.CTkLabel(row_m2, text="Val. Spécifique (Débit / Vapeur / RPM / Ratio MW) :", text_color=THEME["text_muted"]).pack(side="left", padx=(10, 4))
    ent_mach_spec = ctk.CTkEntry(row_m2, width=70, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    ent_mach_spec.pack(side="left", padx=4)
    ent_mach_spec.insert(0, "0.0")
    def charger_specs_machine_mod(nom_m):
        sp = get_machine_specs(nom_m)
        menu_mod_cat.set(sp.get("categorie", "Production"))
        menu_sens_mw.set(sp.get("sens_mw", "Consomme"))
        lbl_mach_mw.configure(text="Production (MW) :" if menu_sens_mw.get() == "Produit" else "Conso (MW) :")
        ent_mach_mw.delete(0, "end"); ent_mach_mw.insert(0, str(sp.get("mw", 15.0)))
        ent_mach_vit.delete(0, "end"); ent_mach_vit.insert(0, str(sp.get("vitesse", 1.0)))
        ent_mach_som.delete(0, "end"); ent_mach_som.insert(0, str(sp.get("somers_max", 1)))
        ent_mach_spec.delete(0, "end"); ent_mach_spec.insert(0, str(sp.get("valeur_spec", 0.0)))
    combo_mod_machine.configure(command=charger_specs_machine_mod)
    def enregistrer_machine_mod():
        nom_m = combo_mod_machine.get().strip()
        if not nom_m:
            return
        try:
            MODS_CONFIG["machines_custom"][nom_m] = {
                "categorie": menu_mod_cat.get(),
                "mw": float(ent_mach_mw.get().strip()),
                "sens_mw": menu_sens_mw.get(),
                "vitesse": float(ent_mach_vit.get().strip()),
                "somers_max": int(float(ent_mach_som.get().strip())),
                "valeur_spec": float(ent_mach_spec.get().strip())
            }
            sauvegarder_mods()
            charger_et_fusionner_donnees()
            synchroniser_usine_active()
            charger_usine_dans_ui(usine_active_nom)
            construire_onglet_mods()
            construire_onglet_auto()
            popup_success("Machine enregistrée", f"La machine '{nom_m}' ({menu_mod_cat.get()}) a été enregistrée !")
        except ValueError:
            popup_error("Erreur", "Vérifiez les valeurs numériques.")
    ctk.CTkButton(row_m1, text="🗑️ Supprimer / Restaurer", corner_radius=8, fg_color="#991B1B", hover_color="#7F1D1D", text_color="#FFFFFF", command=lambda: supprimer_ou_restaurer_machine_specifique(combo_mod_machine.get().strip())).pack(side="right", padx=(4, 10), pady=8)
    ctk.CTkButton(row_m1, text="💾 Enregistrer Machine", corner_radius=8, fg_color="#065F46", hover_color="#047857", text_color="#FFFFFF", command=enregistrer_machine_mod).pack(side="right", padx=4, pady=8)
    machines_modifiees = [m for m in sorted(MODS_CONFIG["machines_custom"].keys()) if est_machine_modifiee_ou_creee(m)]
    frame_liste_mach_custom = ctk.CTkFrame(card_mods_mach, fg_color=THEME["bg_card"])
    frame_liste_mach_custom.pack(fill="x", padx=14, pady=(4, 12))
    ctk.CTkLabel(frame_liste_mach_custom, text="📋 Machines personnalisées ou modifiées actives :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_muted"]).pack(anchor="w", pady=(2, 4))
    if not machines_modifiees:
        ctk.CTkLabel(frame_liste_mach_custom, text="   ✓ Aucune machine modifiée ou créée.", font=ctk.CTkFont(family="Consolas", size=12), text_color=THEME["status_ok"]).pack(anchor="w", pady=2)
    else:
        for m_cust in machines_modifiees:
            sp_c = MODS_CONFIG["machines_custom"][m_cust]
            est_nouvelle = m_cust not in MACHINES_VANILLA
            tag_type = "🆕 CRÉÉE" if est_nouvelle else "🔧 MODIFIÉE"
            lbl_btn_txt = "✕ Supprimer" if est_nouvelle else "↺ Restaurer Vanilla"
            sens_mw = "Production" if sp_c.get("sens_mw", "Consomme") == "Produit" else "Consommation"
            r_mc = ctk.CTkFrame(frame_liste_mach_custom, fg_color=THEME["bg_card_alt"], corner_radius=8)
            r_mc.pack(fill="x", pady=3)
            ctk.CTkLabel(
                r_mc,
                text=f"{tag_type} [{sp_c.get('categorie', 'Production')}] : {m_cust} │ ⚡ {sens_mw} : {sp_c['mw']} MW │ 🚀 x{sp_c['vitesse']} │ 🌀 Somers:{sp_c['somers_max']} │ Spec:{sp_c.get('valeur_spec', 0.0)}",
                font=ctk.CTkFont(family="Consolas", size=11, weight="bold"), text_color=THEME["text_main"]
            ).pack(side="left", padx=10, pady=6)
            ctk.CTkButton(r_mc, text=lbl_btn_txt, width=140, height=26, corner_radius=8, fg_color="#991B1B", text_color="#FFFFFF", command=lambda nom_cible=m_cust: supprimer_ou_restaurer_machine_specifique(nom_cible)).pack(side="right", padx=8, pady=6)
    # Panneau C : Recettes Moddées
    card_mods_rec = ctk.CTkFrame(scroll_mods, fg_color=THEME["bg_card"], border_color=THEME["border"], border_width=1, corner_radius=10)
    card_mods_rec.pack(fill="x", padx=8, pady=8)
    ctk.CTkLabel(card_mods_rec, text="🧪 C. AJOUTER OU SUPPRIMER UNE RECETTE MODDÉE", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=14, pady=(10, 4))
    f_rec_top = ctk.CTkFrame(card_mods_rec, fg_color=THEME["bg_card_alt"], corner_radius=8)
    f_rec_top.pack(fill="x", padx=14, pady=4)
    ctk.CTkLabel(f_rec_top, text="Nom Recette :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4), pady=8)
    ent_rec_nom = ctk.CTkEntry(f_rec_top, width=220, fg_color=THEME["bg_card"], text_color=THEME["text_main"], placeholder_text="ex: Lingot Quantique")
    ent_rec_nom.pack(side="left", padx=4, pady=8)
    ctk.CTkLabel(f_rec_top, text="Bâtiment :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
    combo_rec_bat = ctk.CTkComboBox(f_rec_top, values=liste_machines_prod, width=170, fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    combo_rec_bat.pack(side="left", padx=4)
    combo_rec_bat.set("Constructeur")
    var_rec_alt = ctk.BooleanVar(value=False)
    ctk.CTkCheckBox(f_rec_top, text="Recette Alternative", variable=var_rec_alt, text_color=THEME["text_main"]).pack(side="left", padx=12)
    f_rec_io = ctk.CTkFrame(card_mods_rec, fg_color=THEME["bg_card_alt"], corner_radius=8)
    f_rec_io.pack(fill="x", padx=14, pady=4)
    entrees_widgets = []
    for i in range(4):
        ctk.CTkLabel(f_rec_io, text=f"Entrée {i+1} :", text_color=THEME["text_main"]).grid(row=0, column=i*2, padx=(8, 2), pady=6, sticky="e")
        f_pair = ctk.CTkFrame(f_rec_io, fg_color=THEME["bg_card_alt"])
        f_pair.grid(row=0, column=i*2+1, padx=(0, 8), pady=6)
        e_nom = ctk.CTkEntry(f_pair, width=120, fg_color=THEME["bg_card"], text_color=THEME["text_main"], placeholder_text="Objet")
        e_nom.pack(side="left", padx=2)
        e_qte = ctk.CTkEntry(f_pair, width=50, fg_color=THEME["bg_card"], text_color=THEME["text_main"], placeholder_text="/min")
        e_qte.pack(side="left", padx=2)
        entrees_widgets.append((e_nom, e_qte))
    sorties_widgets = []
    for i in range(2):
        ctk.CTkLabel(f_rec_io, text=f"Sortie {i+1} :", text_color=THEME["text_main"]).grid(row=1, column=i*2, padx=(8, 2), pady=6, sticky="e")
        f_pair = ctk.CTkFrame(f_rec_io, fg_color=THEME["bg_card_alt"])
        f_pair.grid(row=1, column=i*2+1, padx=(0, 8), pady=6)
        s_nom = ctk.CTkEntry(f_pair, width=120, fg_color=THEME["bg_card"], text_color=THEME["text_main"], placeholder_text="Objet produit")
        s_nom.pack(side="left", padx=2)
        s_qte = ctk.CTkEntry(f_pair, width=50, fg_color=THEME["bg_card"], text_color=THEME["text_main"], placeholder_text="/min")
        s_qte.pack(side="left", padx=2)
        sorties_widgets.append((s_nom, s_qte))
    def ajouter_recette_moddee():
        nom_r = ent_rec_nom.get().strip()
        bat_r = combo_rec_bat.get().strip()
        if not nom_r or not sorties_widgets[0][0].get().strip():
            popup_warning("Champs requis", "Indiquez au moins un nom de recette et la Sortie 1.")
            return
        if var_rec_alt.get() and not nom_r.lower().startswith("recette alternative"):
            nom_r = f"Recette alternative : {nom_r}"
        nouvelle = {"Nom de la recette": nom_r, "Objet de base": sorties_widgets[0][0].get().strip(), "Bâtiment": bat_r}
        try:
            for i in range(4):
                n_in = entrees_widgets[i][0].get().strip()
                q_in = entrees_widgets[i][1].get().strip().replace(",", ".")
                nouvelle[f"Entrée {i+1}"] = n_in if n_in else None
                nouvelle[f"Entrée {i+1} / Min"] = float(q_in) if (n_in and q_in) else 0.0
            for i in range(2):
                n_out = sorties_widgets[i][0].get().strip()
                q_out = sorties_widgets[i][1].get().strip().replace(",", ".")
                nouvelle[f"Sortie {i+1}"] = n_out if n_out else None
                nouvelle[f"Sortie {i+1} / Min"] = float(q_out) if (n_out and q_out) else 0.0
        except ValueError:
            popup_error("Erreur", "Les débits (/min) doivent être des nombres valides.")
            return
        MODS_CONFIG["recettes_custom"].append(nouvelle)
        sauvegarder_mods()
        charger_et_fusionner_donnees()
        synchroniser_usine_active()
        charger_usine_dans_ui(usine_active_nom)
        construire_onglet_mods()
        construire_onglet_auto()
        popup_success("Recette ajoutée", f"La recette '{nom_r}' est maintenant disponible !")
    def supprimer_recette_specifique(cible_nom):
        if not popup_askyesno("Supprimer Recette", f"Supprimer la recette moddée '{cible_nom}' ?"):
            return
        MODS_CONFIG["recettes_custom"] = [r for r in MODS_CONFIG["recettes_custom"] if r["Nom de la recette"] != cible_nom]
        sauvegarder_mods()
        charger_et_fusionner_donnees()
        synchroniser_usine_active()
        charger_usine_dans_ui(usine_active_nom)
        construire_onglet_mods()
        construire_onglet_auto()
    f_rec_act = ctk.CTkFrame(card_mods_rec, fg_color=THEME["bg_card"])
    f_rec_act.pack(fill="x", padx=14, pady=(4, 8))
    ctk.CTkButton(f_rec_act, text="+ Enregistrer cette Recette Moddée", corner_radius=8, fg_color="#065F46", text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=ajouter_recette_moddee).pack(side="left")
    frame_liste_rec_custom = ctk.CTkFrame(card_mods_rec, fg_color=THEME["bg_card"])
    frame_liste_rec_custom.pack(fill="x", padx=14, pady=(4, 12))
    for r_c in MODS_CONFIG["recettes_custom"]:
        nom_rc = r_c["Nom de la recette"]
        row_rc = ctk.CTkFrame(frame_liste_rec_custom, fg_color=THEME["bg_card_alt"], corner_radius=8)
        row_rc.pack(fill="x", pady=3)
        ctk.CTkLabel(row_rc, text=f"🧪 {nom_rc} [{r_c.get('Bâtiment', '?')}] ➔ {r_c.get('Sortie 1 / Min', 0)}x {r_c.get('Sortie 1', '')}/min", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=10, pady=6)
        ctk.CTkButton(row_rc, text="✕ Supprimer", width=120, height=26, corner_radius=8, fg_color="#991B1B", text_color="#FFFFFF", command=lambda n_c=nom_rc: supprimer_recette_specifique(n_c)).pack(side="right", padx=8, pady=6)

# ==============================================================================
# 14B. ONGLET 7 : CATALOGUE DES RECETTES, STACKS & CALCULATEUR COFFRES / TRAINS ➔ DS DRIVE
# ==============================================================================
scroll_recettes = FrameDefilantOptimise(tab_recettes, fg_color=THEME["bg_panel"])
scroll_recettes.pack(fill="both", expand=True, padx=6, pady=6)

def construire_onglet_recettes():
    global lbl_cout_construction
    for w in scroll_recettes.winfo_children():
        w.destroy()
    card_cout = ctk.CTkFrame(scroll_recettes, fg_color=THEME["bg_card"], border_color=THEME["status_ok"], border_width=2, corner_radius=12)
    card_cout.pack(fill="x", padx=8, pady=6)
    ctk.CTkLabel(card_cout, text="🏗️ COMBIEN DE MATÉRIAUX POUR CONSTRUIRE L'USINE ?", font=ctk.CTkFont(size=14, weight="bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=14, pady=(10, 2))
    ctk.CTkLabel(card_cout, text="Tu écris ce qu'il faut pour construire un bâtiment. L'appli multiplie ensuite par le nombre de bâtiments. Exemple : 3 béton pour 104 constructeurs = 312 béton.", wraplength=950, justify="left", text_color=THEME["text_muted"]).pack(anchor="w", padx=14, pady=(0, 8))
    batiments_cout = sorted(set(
        list(MODS_CONFIG["machines_custom"].keys()) + list(liste_machines_extraction)
        + [f"Foreuse {tier}" for tier in ("Mk.1", "Mk.2", "Mk.3")]
        + list(FILIERES_ENERGIE.keys()) + [
            DS_TYPE_BAIE, "Contrôleur Réseau Central", "Network Power Adapter",
            "Serveur 1U (Item)", "Serveur 1U (Fluide)", "Serveur 2U (Item)",
            "Serveur 2U (Fluide)", "Serveur 2U (Gaz)", "Serveur de Craft"
        ]
    ))
    batiment_initial = "Constructeur" if "Constructeur" in batiments_cout else batiments_cout[0]
    batiment_cout_var = ctk.StringVar(value=batiment_initial)
    popup_batiments = {"fenetre": None}

    row_cout = ctk.CTkFrame(card_cout, fg_color=THEME["bg_card_alt"], corner_radius=8)
    row_cout.pack(fill="x", padx=14, pady=5)
    row_cout.grid_columnconfigure(1, weight=1)
    ctk.CTkLabel(row_cout, text="Bâtiment :", text_color=THEME["text_main"]).grid(row=0, column=0, padx=(10, 4), pady=8, sticky="w")
    btn_bat_cout = ctk.CTkButton(
        row_cout, text=f"{batiment_initial}  ▾", anchor="w",
        fg_color=THEME["bg_card"], hover_color=THEME["bg_panel"],
        text_color=THEME["text_main"], command=lambda: ouvrir_liste_batiments()
    )
    btn_bat_cout.grid(row=0, column=1, padx=4, pady=6, sticky="ew")
    ctk.CTkLabel(row_cout, text="Nombre de matériaux :", text_color=THEME["text_main"]).grid(row=0, column=2, padx=(10, 3), pady=8, sticky="e")
    ent_nb_couts = ctk.CTkEntry(row_cout, width=55, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    ent_nb_couts.insert(0, "1")
    ent_nb_couts.grid(row=0, column=3, padx=(3, 10), pady=6)
    champs_couts = []
    frame_champs_couts = ctk.CTkFrame(card_cout, fg_color=THEME["bg_card"])
    frame_champs_couts.pack(fill="x", padx=14, pady=(4, 8))
    lbl_cout_batiment = ctk.CTkLabel(card_cout, text="", justify="left", anchor="w", text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=11))
    lbl_cout_batiment.pack(fill="x", padx=14, pady=(4, 2))
    row_actions_cout = ctk.CTkFrame(card_cout, fg_color=THEME["bg_card"])
    row_actions_cout.pack(fill="x", padx=14, pady=(4, 8))
    for column in range(3):
        row_actions_cout.grid_columnconfigure(column, weight=1, uniform="actions")
    lbl_cout_construction = ctk.CTkLabel(card_cout, text="", justify="left", anchor="w", text_color=THEME["status_ok"], font=ctk.CTkFont(family="Consolas", size=12, weight="bold"))
    lbl_cout_construction.pack(fill="x", padx=14, pady=(4, 10))

    def fermer_liste_batiments():
        fenetre = popup_batiments["fenetre"]
        if fenetre is not None and fenetre.winfo_exists():
            fenetre.destroy()
        popup_batiments["fenetre"] = None

    def selectionner_batiment(nom_batiment):
        batiment_cout_var.set(nom_batiment)
        btn_bat_cout.configure(text=f"{nom_batiment}  ▾")
        fermer_liste_batiments()
        afficher_cout_batiment()

    def ouvrir_liste_batiments():
        fenetre_existante = popup_batiments["fenetre"]
        if fenetre_existante is not None and fenetre_existante.winfo_exists():
            fenetre_existante.focus()
            return

        fenetre = ctk.CTkToplevel(app)
        popup_batiments["fenetre"] = fenetre
        fenetre.title("Choisir un bâtiment")
        fenetre.transient(app)
        fenetre.geometry("440x520")
        fenetre.minsize(360, 300)
        fenetre.grid_columnconfigure(0, weight=1)
        fenetre.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(
            fenetre, text="Choisis un bâtiment",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=THEME["text_main"]
        ).grid(row=0, column=0, padx=14, pady=(14, 6), sticky="w")
        recherche_batiments = ctk.CTkEntry(
            fenetre, placeholder_text="Rechercher un bâtiment…",
            fg_color=THEME["bg_card"], text_color=THEME["text_main"]
        )
        recherche_batiments.grid(row=1, column=0, padx=14, pady=(2, 8), sticky="ew")
        liste_batiments = FrameDefilantOptimise(
            fenetre, fg_color=THEME["bg_card"], corner_radius=8
        )
        liste_batiments.grid(row=2, column=0, padx=14, pady=(0, 14), sticky="nsew")
        fenetre.protocol("WM_DELETE_WINDOW", fermer_liste_batiments)

        def actualiser_liste_batiments(_=None):
            for widget in liste_batiments.winfo_children():
                widget.destroy()
            recherche = recherche_batiments.get().strip().casefold()
            resultats = [nom for nom in batiments_cout if recherche in nom.casefold()]
            if not resultats:
                ctk.CTkLabel(
                    liste_batiments, text="Aucun bâtiment trouvé.",
                    text_color=THEME["text_muted"]
                ).pack(fill="x", padx=8, pady=10)
                return
            for nom in resultats:
                ctk.CTkButton(
                    liste_batiments, text=nom, anchor="w",
                    fg_color=THEME["bg_card_alt"], hover_color=THEME["tab_sel"],
                    text_color=THEME["text_main"],
                    command=lambda nom=nom: selectionner_batiment(nom)
                ).pack(fill="x", padx=4, pady=2)

        recherche_batiments.bind("<KeyRelease>", actualiser_liste_batiments)
        actualiser_liste_batiments()
        fenetre.after(50, recherche_batiments.focus_set)

    def valeurs_champs_couts():
        return [
            (champ_nom.get().strip(), champ_qte.get().strip())
            for champ_nom, champ_qte in champs_couts
        ]

    def construire_champs_couts(valeurs=None):
        nonlocal champs_couts
        for widget in frame_champs_couts.winfo_children():
            widget.destroy()
        champs_couts = []
        if valeurs is None:
            recette = MODS_CONFIG.get("couts_construction", {}).get(batiment_cout_var.get(), {})
            valeurs = list(recette.items()) if isinstance(recette, dict) else []
        try:
            nombre = int(ent_nb_couts.get().strip())
        except ValueError:
            popup_error("Nombre incorrect", "Choisis un nombre entier de matériaux.")
            return
        if nombre < 1:
            popup_warning("Nombre incorrect", "Le nombre de matériaux doit être au moins égal à 1.")
            return
        for index in range(nombre):
            ligne = ctk.CTkFrame(frame_champs_couts, fg_color=THEME["bg_card_alt"], corner_radius=6)
            ligne.pack(fill="x", pady=2)
            ctk.CTkLabel(ligne, text=f"Matériau {index + 1} :", width=115, anchor="w", text_color=THEME["text_main"]).pack(side="left", padx=(8, 3), pady=5)
            champ_nom = ctk.CTkEntry(ligne, width=240, placeholder_text="Ex. Béton", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
            champ_nom.pack(side="left", padx=4, pady=5)
            ctk.CTkLabel(ligne, text="Qté / bâtiment :", text_color=THEME["text_main"]).pack(side="left", padx=(8, 3))
            champ_qte = ctk.CTkEntry(ligne, width=90, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
            champ_qte.pack(side="left", padx=4, pady=5)
            if index < len(valeurs):
                champ_nom.insert(0, str(valeurs[index][0]))
                champ_qte.insert(0, str(valeurs[index][1]))
            champs_couts.append((champ_nom, champ_qte))

    def afficher_cout_batiment(*_):
        cout = MODS_CONFIG.get("couts_construction", {}).get(batiment_cout_var.get(), {})
        detail = " • ".join(f"{nom} : {qte:g}" for nom, qte in sorted(cout.items())) if isinstance(cout, dict) else ""
        lbl_cout_batiment.configure(text=f"Pour 1 bâtiment : {detail}" if detail else "Aucun matériau saisi pour ce bâtiment.")
        valeurs = list(cout.items()) if isinstance(cout, dict) else []
        ent_nb_couts.delete(0, "end")
        ent_nb_couts.insert(0, str(max(len(valeurs), 1)))
        construire_champs_couts(valeurs)

    def enregistrer_cout_batiment():
        nom_batiment = batiment_cout_var.get().strip()
        if not nom_batiment or not champs_couts:
            popup_warning("Information manquante", "Choisis un bâtiment et crée au moins une ligne de matériau.")
            return
        recette = {}
        for champ_nom, champ_qte in champs_couts:
            nom_materiau = champ_nom.get().strip()
            try:
                quantite = float(champ_qte.get().strip().replace(",", "."))
            except ValueError:
                popup_error("Quantité incorrecte", "Écris une quantité valide pour chaque matériau, par exemple 3 ou 2,5.")
                return
            if not nom_materiau or quantite <= 0:
                popup_warning("Information manquante", "Chaque ligne doit avoir un matériau et une quantité supérieure à zéro.")
                return
            recette[nom_materiau] = recette.get(nom_materiau, 0.0) + quantite
        MODS_CONFIG.setdefault("couts_construction", {})[nom_batiment] = recette
        sauvegarder_mods()
        afficher_cout_batiment()
        declencher_calcul()

    def supprimer_cout_batiment():
        nom_batiment = batiment_cout_var.get().strip()
        if MODS_CONFIG.get("couts_construction", {}).pop(nom_batiment, None) is not None:
            sauvegarder_mods()
            afficher_cout_batiment()
            declencher_calcul()

    ctk.CTkButton(
        row_actions_cout, text="Créer les lignes", height=36, corner_radius=8,
        fg_color=THEME["tab_sel"], text_color="#FFFFFF",
        command=lambda: construire_champs_couts(valeurs_champs_couts())
    ).grid(row=0, column=0, sticky="ew", padx=(0, 4))
    ctk.CTkButton(
        row_actions_cout, text="💾 Enregistrer les matériaux", height=36, corner_radius=8,
        fg_color="#065F46", text_color="#FFFFFF",
        command=enregistrer_cout_batiment
    ).grid(row=0, column=1, sticky="ew", padx=4)
    ctk.CTkButton(
        row_actions_cout, text="✕ Effacer la recette", height=36, corner_radius=8,
        fg_color="#991B1B", text_color="#FFFFFF",
        command=supprimer_cout_batiment
    ).grid(row=0, column=2, sticky="ew", padx=(4, 0))
    ctk.CTkButton(
        row_actions_cout, text="?", width=30, height=30, corner_radius=15,
        fg_color=THEME["bg_panel"], hover_color=THEME["seg_sel"],
        text_color=THEME["text_main"],
        command=lambda: popup_info(
            "Petite aide",
            "Choisis un bâtiment dans la liste déroulante. Ensuite, choisis le nombre de matériaux et crée les lignes. Exemple : 2 matériaux affichent deux lignes avec leur nom et leur quantité."
        )
    ).grid(row=0, column=3, sticky="e", padx=(4, 0))
    afficher_cout_batiment()

    card_calc = ctk.CTkFrame(scroll_recettes, fg_color=THEME["bg_card"], border_color=THEME["tab_sel"], border_width=2, corner_radius=12)
    card_calc.pack(fill="x", padx=8, pady=6)
    ctk.CTkLabel(card_calc, text="📦 CALCULATEUR DE DISQUES DS DRIVE (ÉQUIVALENCE SIMPLE COFFRE, DOUBLE COFFRE & WAGON DE TRAIN)", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"]).pack(anchor="w", padx=14, pady=(10, 4))

    r_c = ctk.CTkFrame(card_calc, fg_color=THEME["bg_card_alt"], corner_radius=8)
    r_c.pack(fill="x", padx=14, pady=6)
    tous_obj = sorted(list(set(liste_objets_produits + list(STACKS_DEFAUT.keys()))))
    ctk.CTkLabel(r_c, text="Objet :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4), pady=8)
    cb_obj = ctk.CTkComboBox(r_c, values=tous_obj, width=210, fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    cb_obj.pack(side="left", padx=4)
    cb_obj.set("Vis" if "Vis" in tous_obj else tous_obj[0])

    ctk.CTkLabel(r_c, text="Taille Stack :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
    ent_st = ctk.CTkEntry(r_c, width=65, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    ent_st.pack(side="left", padx=4)
    ent_st.insert(0, str(get_stack_objet(cb_obj.get())))

    ctk.CTkLabel(r_c, text="Conteneur cible :", text_color=THEME["text_main"]).pack(side="left", padx=(10, 4))
    seg_cont = ctk.CTkSegmentedButton(r_c, values=["Simple Coffre (24 slots)", "Double Coffre (48 slots)", "Wagon Train (32 slots)"], fg_color=THEME["bg_panel"], selected_color=THEME["seg_sel"], text_color="#FFFFFF")
    seg_cont.set("Double Coffre (48 slots)")
    seg_cont.pack(side="left", padx=6)

    ctk.CTkLabel(r_c, text="Débit Train/Convoyeur (/min) :", text_color=THEME["text_muted"]).pack(side="left", padx=(8, 4))
    ent_deb_tr = ctk.CTkEntry(r_c, width=65, justify="center", fg_color=THEME["bg_card"], text_color=THEME["text_main"])
    ent_deb_tr.insert(0, "780")
    ent_deb_tr.pack(side="left", padx=4)

    lbl_res_calc = ctk.CTkLabel(card_calc, text="", font=ctk.CTkFont(family="Consolas", size=12, weight="bold"), text_color=THEME["status_ok"], justify="left", anchor="w")
    lbl_res_calc.pack(fill="x", padx=14, pady=(4, 10))

    def maj_calcul_stack(*_):
        nom_o = cb_obj.get().strip()
        try:
            st_val = max(int(ent_st.get().strip()), 1)
        except ValueError:
            st_val = get_stack_objet(nom_o)
        MODS_CONFIG["stacks_custom"][nom_o] = st_val
        sauvegarder_mods()
        slots_c = 24 if "24" in seg_cont.get() else (48 if "48" in seg_cont.get() else 32)
        total_items = slots_c * st_val
        try:
            deb = max(float(ent_deb_tr.get().strip()), 1.0)
        except ValueError:
            deb = 780.0
        temps_min = total_items / deb
        paliers_d = [(256, "DS DRIVE 256"), (512, "DS DRIVE 512"), (1000, "DS DRIVE 1K"), (2000, "DS DRIVE 2K"), (4000, "DS DRIVE 4K"), (8000, "DS DRIVE 8K"), (16000, "DS DRIVE 16K"), (32000, "DS DRIVE 32K"), (64000, "DS DRIVE 64K")]
        disque_rec = next((nom_d for cap_d, nom_d in paliers_d if cap_d >= total_items), f"{math.ceil(total_items/64000)}x DS DRIVE 64K")
        lbl_res_calc.configure(
            text=f"🎯 {seg_cont.get()} de '{nom_o}' (Stack de {st_val}) = {slots_c} stacks = {total_items:,} items minimum requis.\n"
                 f"💾 Disque recommandé : {disque_rec}  │  ⏱️ Temps de remplissage/vidage à {deb:g}/min : {temps_min:.1f} min ({temps_min*60:.0f} sec)"
        )

    def on_select_obj_stack(choix):
        ent_st.delete(0, "end")
        ent_st.insert(0, str(get_stack_objet(choix)))
        maj_calcul_stack()

    cb_obj.configure(command=on_select_obj_stack)
    seg_cont.configure(command=maj_calcul_stack)
    ent_st.bind("<KeyRelease>", maj_calcul_stack)
    ent_deb_tr.bind("<KeyRelease>", maj_calcul_stack)
    maj_calcul_stack()

    # Catalogue filtrable des recettes du jeu
    card_cat = ctk.CTkFrame(scroll_recettes, fg_color=THEME["bg_card"], border_color=THEME["border"], border_width=1, corner_radius=12)
    card_cat.pack(fill="both", expand=True, padx=8, pady=6)
    r_flt = ctk.CTkFrame(card_cat, fg_color=THEME["bg_card"])
    r_flt.pack(fill="x", padx=14, pady=(10, 4))
    ctk.CTkLabel(r_flt, text="📚 CATALOGUE DES RECETTES DU JEU & DES MODS (Rechercher un produit ou bâtiment) :", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"]).pack(side="left")
    ent_search_rec = ctk.CTkEntry(r_flt, width=260, placeholder_text="🔍 Filtrer (ex: Acier, Raffinerie, Turbo...)", fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"])
    ent_search_rec.pack(side="right", padx=6)

    box_list_r = ctk.CTkTextbox(card_cat, height=440, fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=12))
    box_list_r.pack(fill="both", expand=True, padx=14, pady=(4, 12))

    def afficher_catalogue_filtre(*_):
        q = ent_search_rec.get().strip().lower()
        box_list_r.configure(state="normal")
        box_list_r.delete("1.0", "end")
        lignes_cat = []
        for _, r in df.iterrows():
            nom_r = str(r.get("Nom de la recette", ""))
            bat_r = str(r.get("Bâtiment", ""))
            s1, q1 = str(r.get("Sortie 1", "")), r.get("Sortie 1 / Min", 0)
            if q and not any(q in x.lower() for x in (nom_r, bat_r, s1)):
                continue
            ins = []
            for idx_i in range(1, 5):
                en, eq = r.get(f"Entrée {idx_i}"), r.get(f"Entrée {idx_i} / Min", 0)
                if pd.notna(en) and pd.notna(eq) and float(eq) > 0:
                    ins.append(f"{float(eq):g} {en}")
            st_s1 = get_stack_objet(s1)
            lignes_cat.append(f"• {nom_r:<38} │ 🏭 {bat_r:<20} │ IN: {', '.join(ins):<38} ➔ OUT: {float(q1):g}/min {s1} (Stack: {st_s1})")
        box_list_r.insert("1.0", "\n".join(lignes_cat[:300]) if lignes_cat else "Aucune recette trouvée.")
        box_list_r.configure(state="disabled")

    ent_search_rec.bind("<KeyRelease>", afficher_catalogue_filtre)
    afficher_catalogue_filtre()

# ==============================================================================
# 14C. ONGLET 8 : WIKI INTERACTIF INTÉGRÉ & ÉDITEUR AVEC IMAGES (STYLE SITE WEB)
# ==============================================================================
DOSSIER_WIKI = os.path.join(DOSSIER_RACINE_DOCS, "Wiki_Pages")
os.makedirs(DOSSIER_WIKI, exist_ok=True)
fichier_wiki_json = os.path.join(DOSSIER_WIKI, "wiki_articles.json")

WIKI_DEFAUT = {
    "🌐 1. Digital Storage — Guide & Disques": {
        "url": "https://docs.ficsit.app/refinedrd/latest/ds/index.html",
        "image": "",
        "texte": (
            "=== DIGITAL STORAGE (WIKI INTÉGRÉ) ===\n\n"
            "• Server Rack : 22 Slots (Units) au total. Permet de mélanger les serveurs 1U (1 slot) et 2U (2 slots).\n"
            "• Serveurs 1U (Item / Fluide) : Prennent 1 slot dans la baie et accueillent 4 DS Drives.\n"
            "• Serveurs 2U (Item / Fluide / Gaz) : Prennent 2 slots dans la baie et accueillent 12 DS Drives.\n"
            "• Crafting Server : Prend 1 slot, automatise le craft à la demande avec les Crafting Adapters.\n\n"
            "=== CAPACITÉ DES DISQUES & PARTITIONS ===\n"
            "• Item Drives : 256, 512, 1K (1 000), 2K (2 000) ➔ 4 partitions max.\n"
            "• Item Drives : 4K (4 000), 8K, 16K, 32K, 64K (64 000 items) ➔ 8 partitions max.\n"
            "• Fluid Drives : 10 m³ (4 partitions max) ; 20, 40, 60, 120, 240 m³ (8 partitions max). 1 m³ = 1 000 Litres.\n"
            "• Gas Drives : 40, 60, 120, 240 m³ (8 partitions max)."
        )
    },
    "⚡ 2. Refined Power — Toutes les Énergies": {
        "url": "https://docs.ficsit.app/refinedrd/latest/rp/index.html",
        "image": "",
        "texte": (
            "=== REFINED POWER — SOURCES D'ÉNERGIE DIRECTES ===\n\n"
            "• Wind Turbines (Éoliennes) : Mk.1 = 30 MW max | Mk.2 = 100 MW max | Mk.3 = 150 MW max (à 300m d'altitude).\n"
            "• Water Turbine Mk.1 : 8 MW (Impur), 20 MW (Normal), 50 MW (Pur) en continu.\n"
            "• Water Dam (Barrage) : 25 à 700 MW (50 MW + 60 m³/min d'eau par section de 10m).\n"
            "• Micro Reactor (Tier 7) : 1 000 MW (1 GW) sans aucun déchet ! Conso : 0.08 Uranium Rod/min ou 0.04 Plutonium/min ou 0.2 DT Core/min.\n"
            "• Modular Reactor (Tier 7-8) : 1 250 MW (25%) ➔ 5 000 MW (100%) ➔ 7 500 MW (150% stable) ➔ 12 500 MW (250%).\n"
            "• Project Icarus (Tier 8) : Icarus Receiver convertit 2 100 m³/min d'Eau en 1 800 m³/min de Vapeur Compressée (alimente 6 Super HV Turbines = 90 000 MW !)."
        )
    },
    "🔥 3. Refined Power — Chaînes Modulaires (Heaters / Boilers / Turbines)": {
        "url": "https://docs.ficsit.app/refinedrd/latest/rp/index.html",
        "image": "",
        "texte": (
            "=== CHAÎNES MODULAIRES REFINED POWER ===\n\n"
            "1. HEATERS (Chaudières) :\n"
            "  • Biomass Heater (500°C max) : Feuilles (240/min), Bois (36/min), Biomasse (20/min), Biocarburant solide (8/min) ➔ 30-45 m³ CO2/min.\n"
            "  • Coal Heater (500°C max) : Charbon (15/min), Coke (25/min), Charbon compacté (7.143/min) ➔ 30 m³ CO2/min.\n"
            "  • Solution Heater (750°C / 1250°C) : Carburant (12 m³/min), Turbocarburant (4 m³/min), Méthane/Rocket (6 m³/min), Sel fondu chaud (60 m³/min), Carburant ionisé (10 m³/min @ 1250°C).\n"
            "  • Nuclear Heater (2000°C max) : Uranium Rod (0.125/min), Plutonium (0.0625/min), DT Core (0.5/min), Deanorium (0.125/min).\n\n"
            "2. BOILERS :\n"
            "  • Boiler Mk.1 : 45 m³/min Eau ➔ 60 m³/min Vapeur HP (plafonne à 500°C).\n"
            "  • Boiler Mk.2 : @500°C (45 Eau ➔ 60 Vap) | @750°C (90 Eau ➔ 120 Vap) | @1250°C (270 Eau ➔ 360 Vap) | @2000°C (450 Eau ➔ 600 Vap).\n\n"
            "3. TURBINES & GENERATORS :\n"
            "  • Turbine Mk.1 : 60 m³ Vapeur HP ➔ 10 000 RPM (+ 60 m³ Vapeur BP).\n"
            "  • Turbine Mk.2 : 120 m³ Vapeur HP ➔ 25 000 RPM (+ 120 m³ Vapeur BP).\n"
            "  • Super HV Turbine : 300 m³ Vapeur Compressée ➔ 100 000 RPM (+ 450 m³ Vapeur BP).\n"
            "  • LV Generator : 150 MW @ 10 000 RPM | MV Generator : 300 MW @ 17 000 RPM | HV Generator : 500 MW @ 25 000 RPM | Super HV Generator : 15 000 MW @ 100 000 RPM."
        )
    }
}

if os.path.exists(fichier_wiki_json):
    try:
        with open(fichier_wiki_json, "r", encoding="utf-8") as f:
            WIKI_DEFAUT.update(json.load(f))
    except Exception:
        pass

def sauvegarder_wiki():
    try:
        with open(fichier_wiki_json, "w", encoding="utf-8") as f:
            json.dump(WIKI_DEFAUT, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

frame_wiki_main = ctk.CTkFrame(tab_wiki, fg_color=THEME["bg_panel"])
frame_wiki_main.pack(fill="both", expand=True, padx=6, pady=6)

def construire_onglet_wiki():
    import webbrowser
    for w in frame_wiki_main.winfo_children():
        w.destroy()
    top_w = ctk.CTkFrame(frame_wiki_main, fg_color=THEME["bg_card"], corner_radius=10)
    top_w.pack(fill="x", padx=8, pady=6)

    ctk.CTkLabel(top_w, text="📖 Article Wiki :", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"]).pack(side="left", padx=(12, 6), pady=10)
    cb_page = ctk.CTkComboBox(top_w, values=list(WIKI_DEFAUT.keys()), width=360, fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"])
    cb_page.pack(side="left", padx=6)
    cb_page.set(list(WIKI_DEFAUT.keys())[0])

    lbl_img_preview = ctk.CTkLabel(frame_wiki_main, text="")
    txt_wiki_ed = ctk.CTkTextbox(frame_wiki_main, fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=13), wrap="word")

    def charger_article_wiki(titre_art):
        art = WIKI_DEFAUT.get(titre_art, {"url": "", "image": "", "texte": ""})
        txt_wiki_ed.delete("1.0", "end")
        txt_wiki_ed.insert("1.0", art.get("texte", ""))
        img_p = art.get("image", "")
        if img_p and os.path.exists(img_p):
            try:
                from PIL import Image
                pil_img = Image.open(img_p)
                ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(420, 240))
                lbl_img_preview.configure(image=ctk_img, text="")
                lbl_img_preview.image = ctk_img
                lbl_img_preview.pack(pady=6)
            except Exception:
                lbl_img_preview.pack_forget()
        else:
            lbl_img_preview.pack_forget()

    def sauver_article_courant():
        t = cb_page.get().strip()
        if not t:
            return
        if t not in WIKI_DEFAUT:
            WIKI_DEFAUT[t] = {"url": "https://docs.ficsit.app/refinedrd/latest/index.html", "image": "", "texte": ""}
        WIKI_DEFAUT[t]["texte"] = txt_wiki_ed.get("1.0", "end-1c")
        sauvegarder_wiki()
        cb_page.configure(values=list(WIKI_DEFAUT.keys()))
        popup_success("Wiki sauvegardé", f"La page '{t}' a été enregistrée !")

    def associer_image_article():
        ch_img = filedialog.askopenfilename(title="Choisir une image pour cet article", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")])
        if not ch_img:
            return
        t = cb_page.get().strip()
        if t not in WIKI_DEFAUT:
            WIKI_DEFAUT[t] = {"url": "", "image": "", "texte": ""}
        dest_img = os.path.join(DOSSIER_WIKI, os.path.basename(ch_img))
        if os.path.abspath(ch_img) != os.path.abspath(dest_img):
            shutil.copy2(ch_img, dest_img)
        WIKI_DEFAUT[t]["image"] = dest_img
        sauvegarder_wiki()
        charger_article_wiki(t)

    cb_page.configure(command=charger_article_wiki)
    ctk.CTkButton(top_w, text="💾 Sauvegarder Texte", corner_radius=8, fg_color="#065F46", text_color="#FFFFFF", command=sauver_article_courant).pack(side="left", padx=4)
    ctk.CTkButton(top_w, text="🖼️ Insérer Image...", corner_radius=8, fg_color=THEME["tab_sel"], text_color="#FFFFFF", command=associer_image_article).pack(side="left", padx=4)
    ctk.CTkButton(top_w, text="🌐 Ouvrir Wiki Officiel", corner_radius=8, fg_color=THEME["accent_purple"], text_color="#FFFFFF", command=lambda: webbrowser.open(WIKI_DEFAUT.get(cb_page.get(), {}).get("url", "https://docs.ficsit.app/refinedrd/latest/index.html"))).pack(side="right", padx=10)

    txt_wiki_ed.pack(fill="both", expand=True, padx=8, pady=(0, 8))
    charger_article_wiki(cb_page.get())

# ==============================================================================
# 15. ZONE DROITE : COCKPIT DE TÉLÉMÉTRIE MULTI-USINES & BILAN DES FLUX
# ==============================================================================
cockpit = ctk.CTkFrame(workspace, width=500, fg_color=THEME["bg_panel"], border_color=THEME["border"], border_width=1, corner_radius=12)
cockpit.pack(side="right", fill="both")
cockpit.pack_propagate(False)
lbl_cockpit_title = ctk.CTkLabel(cockpit, text="🛰️ TÉLÉMÉTRIE RÉSEAU MULTI-USINES", font=ctk.CTkFont(family="Consolas", size=16, weight="bold"), text_color=THEME["text_main"])
lbl_cockpit_title.pack(pady=(12, 6))
box_pwr_telemetry = ctk.CTkFrame(cockpit, fg_color=THEME["bg_card"], corner_radius=10)
box_pwr_telemetry.pack(fill="x", padx=14, pady=6)
lignes_telemetrie_refs = []
def creer_ligne_telemetrie(parent, titre, couleur_val):
    row = ctk.CTkFrame(parent, fg_color=THEME["bg_card"])
    row.pack(fill="x", padx=12, pady=3)
    lbl_t = ctk.CTkLabel(row, text=titre, font=ctk.CTkFont(size=12), text_color=THEME["text_muted"])
    lbl_t.pack(side="left")
    lbl_v = ctk.CTkLabel(row, text="0.0 MW", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color=couleur_val)
    lbl_v.pack(side="right")
    lignes_telemetrie_refs.append((row, lbl_t, lbl_v))
    return lbl_v
lbl_val_mw_usine_active = creer_ligne_telemetrie(box_pwr_telemetry, "Conso. Usine Active :", THEME["text_main"])
lbl_val_mw_conso_globale = creer_ligne_telemetrie(box_pwr_telemetry, "DEMANDE GLOBALE (Toutes Usines) :", THEME["status_warn"])
lbl_val_mw_prod_globale = creer_ligne_telemetrie(box_pwr_telemetry, "PRODUCTION GLOBALE (Tous Parcs) :", THEME["status_ok"])
jauge_reseau = ctk.CTkProgressBar(box_pwr_telemetry, height=12, corner_radius=6, progress_color=THEME["status_ok"])
jauge_reseau.pack(fill="x", padx=12, pady=(8, 4))
jauge_reseau.set(0.0)
lbl_statut_reseau = ctk.CTkLabel(box_pwr_telemetry, text="⚪ Réseau en attente", font=ctk.CTkFont(family="Consolas", size=11, weight="bold"))
lbl_statut_reseau.pack(padx=12, pady=(0, 10))
bar_portee = ctk.CTkFrame(cockpit, fg_color=THEME["bg_panel"])
bar_portee.pack(fill="x", padx=14, pady=(4, 2))
lbl_portee_analyse = ctk.CTkLabel(bar_portee, text="Portée d'analyse :", font=ctk.CTkFont(size=12, weight="bold"), text_color=THEME["text_main"])
lbl_portee_analyse.pack(side="left")
seg_portee_bilan = ctk.CTkSegmentedButton(bar_portee, values=["🏭 Usine Active", "🌐 Toutes Usines"], variable=portee_bilan_var, fg_color=THEME["bg_card_alt"], selected_color=THEME["tab_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=declencher_calcul)
seg_portee_bilan.pack(side="right")
box_kpis = ctk.CTkFrame(cockpit, fg_color=THEME["bg_card"], corner_radius=10)
box_kpis.pack(fill="x", padx=14, pady=6)
for i in range(3):
    box_kpis.grid_columnconfigure(i, weight=1)
kpis_frames_refs = []
def creer_kpi(col, titre):
    f = ctk.CTkFrame(box_kpis, fg_color=THEME["bg_card_alt"], corner_radius=8)
    f.grid(row=0, column=col, padx=6, pady=8, sticky="ew")
    lbl_t = ctk.CTkLabel(f, text=titre, font=ctk.CTkFont(size=10, weight="bold"), text_color=THEME["text_muted"])
    lbl_t.pack(pady=(6, 0))
    lbl_v = ctk.CTkLabel(f, text="0", font=ctk.CTkFont(family="Consolas", size=20, weight="bold"), text_color=THEME["text_main"])
    lbl_v.pack(pady=(0, 6))
    kpis_frames_refs.append((f, lbl_t, lbl_v))
    return lbl_v
lbl_kpi_eclats = creer_kpi(0, "🔋 ÉCLATS REQUIS")
lbl_kpi_somers = creer_kpi(1, "🌀 SOMERSLOOPS")
lbl_kpi_batiments = creer_kpi(2, "🏭 BÂTIMENTS")
box_resume_machines = ctk.CTkFrame(cockpit, fg_color=THEME["bg_card"], corner_radius=8)
box_resume_machines.pack(fill="x", padx=14, pady=(0, 5))
row_resume_machines = ctk.CTkFrame(box_resume_machines, fg_color=THEME["bg_card"])
row_resume_machines.pack(fill="x", padx=8, pady=(4, 0))
ctk.CTkLabel(row_resume_machines, text="Combien de chaque bâtiment ?", font=ctk.CTkFont(size=11, weight="bold"), text_color=THEME["text_main"]).pack(side="left")
ajouter_bouton_aide(row_resume_machines, "Ici, tu vois le nombre de chaque type de bâtiment dans l'usine choisie. Le grand nombre au-dessus compte tout.")
lbl_resume_machines = ctk.CTkTextbox(box_resume_machines, height=72, wrap="word", fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"], font=ctk.CTkFont(family="Consolas", size=10))
lbl_resume_machines.pack(fill="x", padx=8, pady=(2, 6))
lbl_resume_machines.configure(state="disabled")
flux_header = ctk.CTkFrame(cockpit, fg_color=THEME["bg_panel"])
flux_header.pack(fill="x", padx=14, pady=(8, 4))
lbl_bilan_flux_hdr = ctk.CTkLabel(flux_header, text="📊 BILAN NET DES FLUX (/MIN)", font=ctk.CTkFont(family="Consolas", size=13, weight="bold"), text_color=THEME["text_main"])
lbl_bilan_flux_hdr.pack(side="left")
seg_filtre_bilan = ctk.CTkSegmentedButton(flux_header, values=["Tous", "Déficits 🔴", "Surplus 🟢"], variable=filtre_bilan_var, fg_color=THEME["bg_card_alt"], selected_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=11, weight="bold"), command=declencher_calcul)
seg_filtre_bilan.pack(side="right")
scroll_flux = FrameDefilantOptimise(cockpit, fg_color=THEME["bg_card_alt"], corner_radius=10)
scroll_flux.pack(fill="both", expand=True, padx=14, pady=(4, 14))
lbl_flux_global = ctk.CTkFrame(scroll_flux, fg_color=THEME["bg_card_alt"], corner_radius=8)
lbl_flux_global.pack(fill="x", padx=4, pady=4)
# ==============================================================================
# 16. MOTEUR DE RECOLORATION & POPUP D'OPTIONS VISUELLES ARRONDIE
# ==============================================================================
def appliquer_couleurs_dynamiques():
    global THEME
    synchroniser_usine_active()
    THEME = get_theme()
    app.configure(fg_color=THEME["bg_main"])
    workspace.configure(fg_color=THEME["bg_main"])
    header.configure(fg_color=THEME["bg_panel"])
    lbl_main_title.configure(text_color=THEME["text_main"])
    bar_usines.configure(fg_color=THEME["bg_card_alt"])
    lbl_usine_active_hdr.configure(text_color=THEME["text_main"])
    menu_usine_active.configure(fg_color=THEME["tab_sel"], button_color=THEME["seg_sel"], text_color="#FFFFFF")
    btn_options_hdr.configure(fg_color=THEME["tab_sel"], hover_color=THEME["seg_sel"])
    chk_ficsmas_hdr.configure(text_color=THEME["text_main"])
    tabs.configure(
        fg_color=THEME["bg_panel"],
        segmented_button_fg_color=THEME["bg_card_alt"],
        segmented_button_selected_color=THEME["tab_sel"],
        segmented_button_selected_hover_color=THEME["seg_sel"],
        text_color="#FFFFFF"
    )
    for t_frame in [tab_prod, tab_ext, tab_pwr, tab_auto, tab_ds, tab_mods, tab_recettes, tab_wiki]:
        t_frame.configure(fg_color=THEME["bg_panel"])
    for sf in [scroll_ateliers, scroll_foreuses, scroll_parcs_energie, scroll_auto, scroll_ds, scroll_mods, scroll_recettes]:
        recolorer_scrollable(sf, THEME["bg_panel"])
    recolorer_scrollable(scroll_flux, THEME["bg_card_alt"])
    btn_add_atelier_main.configure(fg_color=THEME["tab_sel"], hover_color=THEME["seg_sel"])
    btn_add_foreuse_main.configure(fg_color=THEME["seg_sel"], hover_color=THEME["tab_sel"])
    bar_btns_pwr.configure(fg_color=THEME["bg_panel"])
    cockpit.configure(fg_color=THEME["bg_panel"], border_color=THEME["border"])
    lbl_cockpit_title.configure(text_color=THEME["text_main"])
    box_pwr_telemetry.configure(fg_color=THEME["bg_card"])
    for r_f, l_t, _ in lignes_telemetrie_refs:
        r_f.configure(fg_color=THEME["bg_card"])
        l_t.configure(text_color=THEME["text_muted"])
    lbl_val_mw_usine_active.configure(text_color=THEME["text_main"])
    lbl_val_mw_conso_globale.configure(text_color=THEME["status_warn"])
    lbl_val_mw_prod_globale.configure(text_color=THEME["status_ok"])
    bar_portee.configure(fg_color=THEME["bg_panel"])
    lbl_portee_analyse.configure(text_color=THEME["text_main"])
    seg_portee_bilan.configure(fg_color=THEME["bg_card_alt"], selected_color=THEME["tab_sel"], text_color="#FFFFFF")
    box_kpis.configure(fg_color=THEME["bg_card"])
    box_resume_machines.configure(fg_color=THEME["bg_card"])
    row_resume_machines.configure(fg_color=THEME["bg_card"])
    lbl_resume_machines.configure(fg_color=THEME["bg_card_alt"], text_color=THEME["text_main"])
    for desc in cadres_descriptions_onglets:
        desc.configure(fg_color=THEME["bg_card_alt"])
        for widget in desc.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.configure(text_color=THEME["text_main"])
            elif isinstance(widget, ctk.CTkButton):
                widget.configure(fg_color=THEME["bg_panel"], hover_color=THEME["seg_sel"], text_color=THEME["text_main"])
    for f_k, lt_k, lv_k in kpis_frames_refs:
        f_k.configure(fg_color=THEME["bg_card_alt"])
        lt_k.configure(text_color=THEME["text_muted"])
        lv_k.configure(text_color=THEME["text_main"])
    flux_header.configure(fg_color=THEME["bg_panel"])
    lbl_bilan_flux_hdr.configure(text_color=THEME["text_main"])
    seg_filtre_bilan.configure(fg_color=THEME["bg_card_alt"], selected_color=THEME["seg_sel"], text_color="#FFFFFF")
    lbl_flux_global.configure(fg_color=THEME["bg_card_alt"])
    for label, statut in labels_flux_bilan:
        couleur = {
            "deficit": THEME["status_err"],
            "surplus": THEME["status_ok"],
            "equilibre": THEME["text_main"]
        }[statut]
        label.configure(text_color=couleur)
    ctk.set_appearance_mode(THEME["ctk_mode"])
    charger_usine_dans_ui(usine_active_nom)
    construire_onglet_auto()
    construire_onglet_mods()
    construire_onglet_recettes()
    construire_onglet_wiki()
def ouvrir_fenetre_options():
    win = ctk.CTkToplevel(app)
    win.title("Options Visuelles")
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.transient(app)
    trans_key = "#000001"
    try:
        if os.name == "nt":
            win.configure(fg_color=trans_key)
            win.wm_attributes("-transparentcolor", trans_key)
        else:
            win.configure(fg_color=THEME["bg_main"])
    except Exception:
        win.configure(fg_color=THEME["bg_main"])
    largeur, hauteur = 620, 490
    win.update_idletasks()
    x = app.winfo_rootx() + (app.winfo_width() - largeur) // 2
    y = app.winfo_rooty() + (app.winfo_height() - hauteur) // 2
    win.geometry(f"{largeur}x{hauteur}+{max(x, 40)}+{max(y, 40)}")
    card = ctk.CTkFrame(win, fg_color=THEME["bg_panel"], border_color=THEME["tab_sel"], border_width=2, corner_radius=18)
    card.pack(fill="both", expand=True, padx=2, pady=2)
    hdr = ctk.CTkFrame(card, fg_color=THEME["bg_card_alt"], corner_radius=14, height=44)
    hdr.pack(fill="x", padx=8, pady=(8, 12))
    lbl_t = ctk.CTkLabel(hdr, text="🎨  PERSONNALISATION DU THÈME & DES COULEURS", font=ctk.CTkFont(family="Consolas", size=14, weight="bold"), text_color=THEME["text_main"])
    lbl_t.pack(side="left", padx=14, pady=8)
    ctk.CTkButton(hdr, text="✕", width=28, height=26, corner_radius=8, fg_color=THEME["bg_card"], hover_color=THEME["status_err"], text_color=THEME["text_main"], command=win.destroy).pack(side="right", padx=8, pady=6)
    drag_state = {"x": 0, "y": 0}
    def _s_move(e): drag_state["x"], drag_state["y"] = e.x, e.y
    def _o_move(e): win.geometry(f"+{win.winfo_x() + (e.x - drag_state['x'])}+{win.winfo_y() + (e.y - drag_state['y'])}")
    for w_d in (hdr, lbl_t):
        w_d.bind("<ButtonPress-1>", _s_move)
        w_d.bind("<B1-Motion>", _o_move)
    f_th = ctk.CTkFrame(card, fg_color=THEME["bg_card"], corner_radius=12)
    f_th.pack(fill="x", padx=20, pady=8)
    lbl_1 = ctk.CTkLabel(f_th, text="1. Thème de l'interface :", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"])
    lbl_1.pack(anchor="w", padx=14, pady=(10, 4))
    f_tab = ctk.CTkFrame(card, fg_color=THEME["bg_card"], corner_radius=12)
    f_seg = ctk.CTkFrame(card, fg_color=THEME["bg_card"], corner_radius=12)
    def rafraichir_modal_options():
        card.configure(fg_color=THEME["bg_panel"], border_color=THEME["tab_sel"])
        hdr.configure(fg_color=THEME["bg_card_alt"])
        lbl_t.configure(text_color=THEME["text_main"])
        for f_b in (f_th, f_tab, f_seg):
            f_b.configure(fg_color=THEME["bg_card"])
        for l_b in (lbl_1, lbl_2, lbl_3):
            l_b.configure(text_color=THEME["text_main"])
        row_t.configure(fg_color=THEME["bg_card"])
        row_s.configure(fg_color=THEME["bg_card"])
        seg_th.configure(fg_color=THEME["bg_card_alt"], selected_color=THEME["tab_sel"])
        btn_hex_tab.configure(fg_color=THEME["tab_sel"])
        btn_hex_seg.configure(fg_color=THEME["seg_sel"])
    def chg_theme(val):
        USER_SETTINGS["theme_nom"] = val
        sauvegarder_settings()
        appliquer_couleurs_dynamiques()
        rafraichir_modal_options()
    seg_th = ctk.CTkSegmentedButton(f_th, values=["Sombre", "Abyssal", "Clair"], fg_color=THEME["bg_card_alt"], selected_color=THEME["tab_sel"], text_color="#FFFFFF", command=chg_theme)
    seg_th.set(USER_SETTINGS.get("theme_nom", "Sombre"))
    seg_th.pack(fill="x", padx=14, pady=(4, 12))
    f_tab.pack(fill="x", padx=20, pady=8)
    lbl_2 = ctk.CTkLabel(f_tab, text="2. Couleur des Onglets Sélectionnés :", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"])
    lbl_2.pack(anchor="w", padx=14, pady=(10, 4))
    row_t = ctk.CTkFrame(f_tab, fg_color=THEME["bg_card"])
    row_t.pack(fill="x", padx=14, pady=(4, 12))
    def chg_preset_tab(nom_p):
        USER_SETTINGS["tab_selected_color"] = COULEURS_PRESETS[nom_p]
        sauvegarder_settings()
        appliquer_couleurs_dynamiques()
        rafraichir_modal_options()
    menu_p_tab = ctk.CTkOptionMenu(row_t, values=list(COULEURS_PRESETS.keys()), width=250, corner_radius=8, command=chg_preset_tab)
    menu_p_tab.pack(side="left", padx=(0, 10))
    def pick_custom_tab():
        c = colorchooser.askcolor(title="Couleur des onglets sélectionnés", initialcolor=USER_SETTINGS["tab_selected_color"])
        if c and c[1]:
            USER_SETTINGS["tab_selected_color"] = c[1]
            sauvegarder_settings()
            appliquer_couleurs_dynamiques()
            rafraichir_modal_options()
    btn_hex_tab = ctk.CTkButton(row_t, text="🌈 Couleur Libre (Hex)...", corner_radius=8, fg_color=THEME["tab_sel"], text_color="#FFFFFF", command=pick_custom_tab)
    btn_hex_tab.pack(side="left")
    f_seg.pack(fill="x", padx=20, pady=8)
    lbl_3 = ctk.CTkLabel(f_seg, text="3. Couleur des Boutons de Cadence Sélectionnés :", font=ctk.CTkFont(size=13, weight="bold"), text_color=THEME["text_main"])
    lbl_3.pack(anchor="w", padx=14, pady=(10, 4))
    row_s = ctk.CTkFrame(f_seg, fg_color=THEME["bg_card"])
    row_s.pack(fill="x", padx=14, pady=(4, 12))
    def chg_preset_seg(nom_p):
        USER_SETTINGS["seg_selected_color"] = COULEURS_PRESETS[nom_p]
        sauvegarder_settings()
        appliquer_couleurs_dynamiques()
        rafraichir_modal_options()
    menu_p_seg = ctk.CTkOptionMenu(row_s, values=list(COULEURS_PRESETS.keys()), width=250, corner_radius=8, command=chg_preset_seg)
    menu_p_seg.pack(side="left", padx=(0, 10))
    def pick_custom_seg():
        c = colorchooser.askcolor(title="Couleur des boutons sélectionnés", initialcolor=USER_SETTINGS["seg_selected_color"])
        if c and c[1]:
            USER_SETTINGS["seg_selected_color"] = c[1]
            sauvegarder_settings()
            appliquer_couleurs_dynamiques()
            rafraichir_modal_options()
    btn_hex_seg = ctk.CTkButton(row_s, text="🌈 Couleur Libre (Hex)...", corner_radius=8, fg_color=THEME["seg_sel"], text_color="#FFFFFF", command=pick_custom_seg)
    btn_hex_seg.pack(side="left")
    ctk.CTkButton(card, text="✓  TERMINÉ", width=160, height=36, corner_radius=10, fg_color=THEME["tab_sel"], hover_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=win.destroy).pack(pady=14)
    win.bind("<Escape>", lambda e: win.destroy())
btn_options_hdr = ctk.CTkButton(header, text="⚙️ THÈMES", width=110, corner_radius=8, fg_color=THEME["tab_sel"], hover_color=THEME["seg_sel"], text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"), command=ouvrir_fenetre_options)
btn_options_hdr.pack(side="right", padx=(4, 14), pady=12)
btn_verifier_maj = ctk.CTkButton(
    header, text="⬆️ MISE À JOUR", width=125, corner_radius=8,
    fg_color=THEME["seg_sel"], hover_color=THEME["tab_sel"],
    text_color="#FFFFFF", font=ctk.CTkFont(size=12, weight="bold"),
    command=lambda: verifier_mises_a_jour(manuelle=True)
)
btn_verifier_maj.pack(side="right", padx=4, pady=12)
ctk.CTkButton(header, text="📂 Importer", width=95, corner_radius=8, fg_color="#334155", text_color="#FFFFFF", command=charger_projet_complet).pack(side="right", padx=4, pady=12)
ctk.CTkButton(header, text="💾 Exporter", width=95, corner_radius=8, fg_color="#065F46", text_color="#FFFFFF", command=sauvegarder_projet_complet).pack(side="right", padx=4, pady=12)
def on_toggle_ficsmas_global():
    charger_et_fusionner_donnees()
    for c in cartes_ateliers:
        c.update_recettes()
    construire_onglet_auto()
chk_ficsmas_hdr = ctk.CTkCheckBox(header, text="🎄 FICSMAS", variable=ficsmas_actif, text_color=THEME["text_main"], command=on_toggle_ficsmas_global)
chk_ficsmas_hdr.pack(side="right", padx=8)
# ==============================================================================
# 17. DÉMARRAGE INITIAL
# ==============================================================================
construire_onglet_mods()
construire_onglet_recettes()
construire_onglet_wiki()
charger_usine_dans_ui(usine_active_nom)
construire_onglet_auto()
appliquer_couleurs_dynamiques()
app.after(1800, lambda: verifier_mises_a_jour(manuelle=False))
app.mainloop()
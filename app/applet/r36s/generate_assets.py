import os

categories = [
    "branding", "icons", "navigation", "actions", "storage",
    "transfer", "systems", "status", "dialogs", "backgrounds",
    "decorative", "sprites", "ui"
]

base_dir = "r36s/assets"

def create_dirs():
    for cat in categories:
        os.makedirs(os.path.join(base_dir, cat), exist_ok=True)
    print("Asset directories created successfully.")

def svg_icon(inner_svg, viewBox="0 0 24 24"):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewBox}" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{inner_svg}</svg>'''

assets_to_create = {
    "branding/logo_main.svg": svg_icon('<path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="#a78bfa" stroke-width="2.5"/><circle cx="12" cy="12" r="3" fill="#38bdf8"/>', "0 0 24 24"),
    "branding/logo_compact.svg": svg_icon('<rect x="2" y="2" width="20" height="20" rx="6" fill="#161520" stroke="#8b5cf6"/><circle cx="12" cy="12" r="5" fill="#38bdf8"/>', "0 0 24 24"),
    "branding/favicon.svg": svg_icon('<circle cx="12" cy="12" r="10" fill="#8b5cf6"/><path d="M8 12l3 3 5-5" stroke="#fff" stroke-width="2"/>', "0 0 24 24"),

    "icons/file_generic.svg": svg_icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>', "0 0 24 24"),
    "icons/file_text.svg": svg_icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>', "0 0 24 24"),
    "icons/file_image.svg": svg_icon('<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/>', "0 0 24 24"),
    "icons/file_video.svg": svg_icon('<polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>', "0 0 24 24"),
    "icons/file_audio.svg": svg_icon('<path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/>', "0 0 24 24"),
    "icons/file_zip.svg": svg_icon('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/>', "0 0 24 24"),
    "icons/file_rom.svg": svg_icon('<rect x="2" y="6" width="20" height="12" rx="2"/><line x1="6" y1="12" x2="10" y2="12"/><line x1="8" y1="10" x2="8" y2="14"/><circle cx="15" cy="11" r="1"/><circle cx="18" cy="13" r="1"/>', "0 0 24 24"),

    "icons/folder.svg": svg_icon('<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>', "0 0 24 24"),
    "icons/folder_open.svg": svg_icon('<path d="m6 14 1.5-2.9A2 2 0 0 1 9.3 10H22v7a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5c0-1.1.9-2 2-2h3.93a2 2 0 0 1 1.66.9l.82 1.2a2 2 0 0 0 1.66.9H18a2 2 0 0 1 2 2v2"/>', "0 0 24 24"),
    "icons/folder_rom.svg": svg_icon('<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="3" stroke="#38bdf8"/>', "0 0 24 24"),

    "navigation/back.svg": svg_icon('<line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/>', "0 0 24 24"),
    "navigation/forward.svg": svg_icon('<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>', "0 0 24 24"),
    "navigation/home.svg": svg_icon('<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>', "0 0 24 24"),
    "navigation/search.svg": svg_icon('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>', "0 0 24 24"),
    "navigation/refresh.svg": svg_icon('<path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.73-5.19"/>', "0 0 24 24"),

    "actions/new_folder.svg": svg_icon('<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="9" y1="14" x2="15" y2="14"/>', "0 0 24 24"),
    "actions/upload.svg": svg_icon('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>', "0 0 24 24"),
    "actions/download.svg": svg_icon('<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>', "0 0 24 24"),
    "actions/copy.svg": svg_icon('<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>', "0 0 24 24"),
    "actions/move.svg": svg_icon('<polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/>', "0 0 24 24"),
    "actions/rename.svg": svg_icon('<path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z"/>', "0 0 24 24"),
    "actions/delete.svg": svg_icon('<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>', "0 0 24 24"),
    "actions/zip.svg": svg_icon('<path d="M4 22h14a2 2 0 0 0 2-2V7.5L14.5 2H6a2 2 0 0 0-2 2v4"/><polyline points="14 2 14 8 20 8"/><path d="M2 12h6"/><path d="M2 16h6"/><path d="M2 8h2"/>', "0 0 24 24"),

    "storage/sd.svg": svg_icon('<path d="M6 2h9l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2z"/><line x1="10" y1="6" x2="10" y2="10"/><line x1="13" y1="6" x2="13" y2="10"/>', "0 0 24 24"),
    "storage/usb.svg": svg_icon('<circle cx="12" cy="5" r="2"/><path d="M12 7v5l-4 3v4h8v-4l-4-3z"/><path d="M9 19h6"/>', "0 0 24 24"),
    "storage/server.svg": svg_icon('<rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/>', "0 0 24 24"),

    "transfer/speed.svg": svg_icon('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>', "0 0 24 24"),
    "transfer/progress.svg": svg_icon('<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>', "0 0 24 24"),

    "systems/gb.svg": svg_icon('<rect x="4" y="2" width="16" height="20" rx="2"/><rect x="7" y="5" width="10" height="7" fill="#38bdf8" fill-opacity="0.2"/><circle cx="8" cy="16" r="1.5"/><circle cx="16" cy="15" r="1"/><circle cx="14" cy="17" r="1"/>', "0 0 24 24"),
    "systems/gba.svg": svg_icon('<rect x="2" y="6" width="20" height="12" rx="4"/><rect x="7" y="8" width="10" height="6" fill="#8b5cf6" fill-opacity="0.2"/><circle cx="5" cy="12" r="1.5"/><circle cx="19" cy="12" r="1"/><circle cx="17" cy="14" r="1"/>', "0 0 24 24"),
    "systems/snes.svg": svg_icon('<rect x="3" y="6" width="18" height="12" rx="2"/><circle cx="7" cy="12" r="2"/><circle cx="17" cy="11" r="1"/><circle cx="15" cy="13" r="1"/><circle cx="17" cy="15" r="1"/><circle cx="19" cy="13" r="1"/>', "0 0 24 24"),
    "systems/nes.svg": svg_icon('<rect x="2" y="7" width="20" height="10" rx="1"/><rect x="5" y="10" width="4" height="4"/><circle cx="15" cy="12" r="1"/><circle cx="18" cy="12" r="1"/>', "0 0 24 24"),
    "systems/n64.svg": svg_icon('<polygon points="12 2 22 20 2 20"/><circle cx="12" cy="13" r="3"/>', "0 0 24 24"),
    "systems/nds.svg": svg_icon('<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="12" x2="21" y2="12"/>', "0 0 24 24"),
    "systems/ps1.svg": svg_icon('<circle cx="12" cy="12" r="10"/><path d="M10 8l6 4-6 4V8z"/>', "0 0 24 24"),
    "systems/psp.svg": svg_icon('<rect x="2" y="6" width="20" height="12" rx="3"/><circle cx="6" cy="12" r="2"/><circle cx="18" cy="12" r="2"/>', "0 0 24 24"),
    "systems/megadrive.svg": svg_icon('<rect x="2" y="7" width="20" height="10" rx="2"/><circle cx="6" cy="12" r="1.5"/><circle cx="10" cy="12" r="1"/><circle cx="13" cy="12" r="1"/><circle cx="16" cy="12" r="1"/>', "0 0 24 24"),
    "systems/arcade.svg": svg_icon('<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M12 14v4"/><circle cx="12" cy="10" r="3"/><circle cx="8" cy="18" r="1"/><circle cx="16" cy="18" r="1"/>', "0 0 24 24"),

    "status/success.svg": svg_icon('<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>', "0 0 24 24"),
    "status/error.svg": svg_icon('<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>', "0 0 24 24"),
    "status/warning.svg": svg_icon('<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>', "0 0 24 24"),
    "status/wifi.svg": svg_icon('<path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/>', "0 0 24 24"),

    "dialogs/info.svg": svg_icon('<circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/>', "0 0 24 24"),
    "dialogs/qr.svg": svg_icon('<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/><line x1="14" y1="14" x2="21" y2="21"/><line x1="14" y1="18" x2="18" y2="18"/>', "0 0 24 24"),

    "backgrounds/grid_pattern.svg": '''<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><path d="M40 0H0V40H40V0Z" fill="none"/><path d="M40 39H0V40H40V39ZM39 40V0H40V40H39Z" fill="rgba(255,255,255,0.02)"/></svg>''',
    "decorative/glow_orb.svg": '''<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200"><circle cx="100" cy="100" r="100" fill="url(#grad)" opacity="0.15"/><defs><radialGradient id="grad" cx="50%" cy="50%" r="50%"><stop offset="0%" stop-color="#8b5cf6"/><stop offset="100%" stop-color="#38bdf8" stop-opacity="0"/></radialGradient></defs></svg>''',

    "sprites/dpad.svg": svg_icon('<path d="M9 2h6v6h6v6h-6v6H9v-6H3V8h6V2z" fill="#161520" stroke="#8b5cf6" stroke-width="2"/>', "0 0 24 24"),
    "sprites/btn_a.svg": svg_icon('<circle cx="12" cy="12" r="10" fill="#161520" stroke="#38bdf8" stroke-width="2"/><text x="12" y="16" font-size="10" text-anchor="middle" fill="#38bdf8" font-family="sans-serif" font-weight="bold">A</text>', "0 0 24 24"),
    "sprites/btn_b.svg": svg_icon('<circle cx="12" cy="12" r="10" fill="#161520" stroke="#8b5cf6" stroke-width="2"/><text x="12" y="16" font-size="10" text-anchor="middle" fill="#8b5cf6" font-family="sans-serif" font-weight="bold">B</text>', "0 0 24 24"),

    "ui/badge_rom.svg": svg_icon('<rect x="2" y="4" width="20" height="16" rx="3" fill="#8b5cf6" fill-opacity="0.2" stroke="#8b5cf6"/><text x="12" y="15" font-size="8" text-anchor="middle" fill="#a78bfa" font-family="sans-serif" font-weight="bold">ROM</text>', "0 0 24 24"),
}

def generate_all():
    for cat in categories:
        os.makedirs(os.path.join(base_dir, cat), exist_ok=True)
    count = 0
    for path, content in assets_to_create.items():
        full_path = os.path.join(base_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        count += 1
    print(f"Successfully generated {count} asset files in {base_dir}/.")

if __name__ == '__main__':
    generate_all()

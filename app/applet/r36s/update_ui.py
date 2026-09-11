import os

ui_path = "r36s/ui.html"
with open(ui_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update brand icon & badge
old_brand = '<div class="brand-icon">🎮</div>\n      <span>R36S Files</span>\n      <span class="brand-badge">iOS Liquid Glass</span>'
new_brand = '<div class="brand-icon"><img src="/assets/branding/logo_main.svg" width="22" height="22"></div>\n      <span>R36S File Manager</span>\n      <span class="brand-badge">dArkOS RE</span>'

if old_brand in content:
    content = content.replace(old_brand, new_brand, 1)
    print("Updated brand successfully.")

# 2. Update getFileIcon
old_get_file_icon = '''      function getFileIcon(name, isDir) {
        if (isDir) return { icon: '📁', class: 'icon-folder' };
        const ext = name.split('.').pop().toLowerCase();
        if (romExtensions[ext]) return { icon: '🎮', class: 'icon-rom', badge: romExtensions[ext] };
        if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return { icon: '📦', class: 'icon-archive', badge: ext.toUpperCase() };
        return { icon: '📄', class: 'icon-file' };
      }'''

new_get_file_icon = '''      function getFileIcon(name, isDir) {
        if (isDir) {
          const lower = name.toLowerCase();
          if (['gba', 'gb', 'snes', 'nes', 'n64', 'nds', 'ps1', 'psp', 'megadrive', 'arcade'].includes(lower)) {
            return { icon: '<img src="/assets/icons/folder_rom.svg" width="20" height="20">', class: 'icon-folder', badge: lower.toUpperCase() };
          }
          return { icon: '<img src="/assets/icons/folder.svg" width="20" height="20">', class: 'icon-folder' };
        }
        const ext = name.split('.').pop().toLowerCase();
        if (romExtensions[ext]) {
          return { icon: '<img src="/assets/icons/file_rom.svg" width="20" height="20">', class: 'icon-rom', badge: romExtensions[ext] };
        }
        if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) {
          return { icon: '<img src="/assets/icons/file_zip.svg" width="20" height="20">', class: 'icon-archive', badge: ext.toUpperCase() };
        }
        if (['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(ext)) {
          return { icon: '<img src="/assets/icons/file_image.svg" width="20" height="20">', class: 'icon-image' };
        }
        if (['mp3', 'wav', 'ogg', 'flac'].includes(ext)) {
          return { icon: '<img src="/assets/icons/file_audio.svg" width="20" height="20">', class: 'icon-audio' };
        }
        if (['mp4', 'mkv', 'avi', 'webm'].includes(ext)) {
          return { icon: '<img src="/assets/icons/file_video.svg" width="20" height="20">', class: 'icon-video' };
        }
        if (['txt', 'log', 'cfg', 'ini', 'gptk'].includes(ext)) {
          return { icon: '<img src="/assets/icons/file_text.svg" width="20" height="20">', class: 'icon-text' };
        }
        return { icon: '<img src="/assets/icons/file_generic.svg" width="20" height="20">', class: 'icon-file' };
      }'''

if old_get_file_icon in content:
    content = content.replace(old_get_file_icon, new_get_file_icon, 1)
    print("Updated getFileIcon successfully.")

# 3. Update renderStorageBar
old_storage = 'pill.innerHTML = `<span>💾</span> <strong>${root.name || root.path}</strong> <span style="opacity: 0.6; font-size: 0.75rem;">(${formatSize(root.free_space)} livres)</span>`;'
new_storage = 'pill.innerHTML = `<img src="/assets/storage/sd.svg" width="16" height="16" style="vertical-align: middle; margin-right: 6px;"> <strong>${root.name || root.path}</strong> <span style="opacity: 0.6; font-size: 0.75rem;">(${formatSize(root.free_space)} livres)</span>`;'

if old_storage in content:
    content = content.replace(old_storage, new_storage, 1)
    print("Updated renderStorageBar successfully.")

with open(ui_path, "w", encoding="utf-8") as f:
    f.write(content)
print("ui.html updated successfully.")

# Cài đặt và kiểm chứng CachyOS

Quy trình dùng [hướng dẫn chuyển DE của CachyOS](https://wiki.cachyos.org/configuration/desktop_environments/switch_desktop/) và danh sách `[desktop.xfce]` từ [CachyOS/New-Cli-Installer](https://github.com/CachyOS/New-Cli-Installer/blob/master/net-profiles.toml). Bản danh sách được lưu tại `config/cachyos-xfce-packages.txt`. Đã bỏ mục lỗi thời `xfce4-datetime-plugin` vì repository hiện không còn package này; [DateTime đã hợp nhất vào Clock của xfce4-panel từ Xfce 4.18](https://xfce.org/about/tour418). Wiki hiện mô tả XFCE là bản vanilla, không có gói `cachyos-xfce-settings` riêng trong danh sách đang hỗ trợ; không tự cài một gói settings dựa trên phỏng đoán.

## Thứ tự thực hiện

1. Tạo snapshot hệ thống, snapshot home và bản nén repo.
2. Gỡ nhóm Plasma và `cachyos-kde-settings` nếu còn; nếu đã gỡ thì ghi nhận và bỏ qua bước này.
3. Cài bộ XFCE đúng danh sách CachyOS, chọn LightDM cho lần boot sau.
4. Kiểm tra XFCE mặc định trước khi áp dụng cấu hình repo.
5. Cài phụ thuộc bổ sung, build các công cụ, áp dụng `home/` và kiểm tra lại.

```bash
bash scripts/installer.sh --snapshot
bash scripts/installer.sh --baseline
bash scripts/installer.sh --build
```

Bước `--baseline` cài lần lượt bộ XFCE mặc định và các phụ thuộc build trong cùng lượt xác thực; chưa áp dụng cấu hình cá nhân. Có thể dùng riêng `--packages` để bổ sung phụ thuộc về sau. Các bước hệ thống dùng PolicyKit và yêu cầu xác thực quản trị. Chạy script bằng tài khoản desktop thường; không chạy build/apply bằng root. Pacman dùng nâng cấp toàn hệ thống `-Syu`, không partial upgrade. Không yêu cầu cài trực tiếp `zlib`: CachyOS có thể dùng `zlib-ng-compat` để cung cấp cùng ABI/header/pkg-config; ép cài `zlib` gây xung đột provider. Các phụ thuộc GTK/libpng bảo đảm provider cần thiết. Script không tự reboot hoặc dừng display manager đang phục vụ phiên đăng nhập.

Snapshot yêu cầu root và home dùng Btrfs trên cùng filesystem, có Snapper config `root`. Root snapshot không bao phủ `/home` vì là subvolume riêng, nên tạo thêm snapshot read-only của `/home`. Repo trên ext4 được nén riêng. Backup repo mặc định nằm trong `/var/lib/miserable-xfce/backups/`; có thể đặt thư mục khác bằng `bash scripts/installer.sh --snapshot /mnt/data/Backups/Miserable_Xfce`. Vị trí snapshot/backup được ghi trong `/var/lib/miserable-xfce/latest-snapshot`; cần giữ cả root, home và repo để quay lại đầy đủ. Không hoàn tác home trong khi người dùng đang đăng nhập. Nếu cài mới trên máy khác, xác nhận bố cục filesystem trước khi chạy bước snapshot.

Để kiểm tra ngay trong phiên XFCE hiện có mà vẫn giữ các cửa sổ ứng dụng:

```bash
python scripts/session.py baseline
# Kiểm tra panel mặc định, theme Adwaita / icon elementary.
python scripts/session.py apply
```

`baseline` lưu bản sao cấu hình desktop, dừng các widget/service tùy chỉnh, đặt lại xfconf qua D-Bus từ `/etc/xdg/xfce4` và mở panel mặc định. Giữ bố cục màn hình, bộ gõ, âm thanh và dữ liệu ứng dụng. `apply` nạp cấu hình từ mã nguồn cũng qua D-Bus để tránh xfconfd ghi ngược file cũ. Đây là kiểm tra desktop trong cùng phiên X11; không thay thế việc kiểm tra đăng nhập LightDM sau reboot.

Cách thông thường trên máy mới: đăng xuất desktop, chuyển TTY bằng Ctrl+Alt+F3, đăng nhập tài khoản thường, rồi:

```bash
bash scripts/installer.sh --apply
```

Có thể xem trước mà không ghi file:

```bash
python scripts/apply.py --include-built --dry-run
```

Apply tạo bản sao lưu file bị thay tại `~/.local/state/miserable-xfce/backups/` và in lệnh rollback. File `~/.config/eww/settings.toml` đã có được giữ nguyên. Sau khi đăng nhập Xfce X11, service neo sidebar, Skippy Overview, Cortile và phím Windows được khởi động qua autostart sau khi import môi trường X11. Các unit này là static; không cần `systemctl --user enable`. Script đăng nhập tự gỡ liên kết `default.target.wants` cũ của bốn unit để tránh khởi động trước khi có DISPLAY.

## Cấu hình và phụ thuộc

Xem [cấu hình cá nhân](settings.md) trước khi cài cho tài khoản khác. Chrome/VS Code/Pamac là lựa chọn trong TOML; cài các app này hoặc đổi sang app đã có. Bộ gõ Fcitx, audio stack, DAC Simgot và driver tạo màn hình ảo RustDesk thuộc cấu hình máy, không bị installer desktop tự thay thế. Script/phím tắt chuyển màn hình thật/ảo được cài từ repo; tên cổng và mode nằm trong `[display]` của TOML. Chúng nằm trong snapshot home/hệ thống để phục hồi máy nguồn.

Giữ các nguồn đang cần: Eww (vá thời gian IPC/compatibility), Skippy + Chipmunk (vá Ctrl+Tab/icon/DISPLAY), plugin PulseAudio (chuyển stream và chụp menu), Cortile release x86_64, xcape từ package và Numix/Numix-Circle. Chỉ giữ GTK 3/4 của Lavanda, Miserable-Chrome, font đang dùng và một hình nền được chọn. Đã bỏ profile riêng, bộ icon/theme cũ, widget Gmail/Spotify helper cũ, script Picom fork và các bản cài đa distro không dùng.

CachyOS là rolling release: source tự build được khóa phiên bản, còn package hệ thống theo repository hiện tại. Biên dịch và chạy tests không chứng minh driver/thiết bị khác hoạt động giống máy nguồn.

## Kiểm tra sau cài

- Panel dưới, widget Sidebar/System Stats, 4 workspace và các plugin đều có.
- Chạm Windows mở Whisker; Ctrl+Space mở Applications; Ctrl+Tab bật/tắt Overview.
- Data đọc đúng filesystem đã cấu hình; thời tiết hiển thị địa điểm mới khi đổi TOML.
- Sidebar neo đúng sau đổi độ phân giải; nhạc MPRIS hiện/ẩn theo trình phát.
- Print/Shift+Print/Alt+Print chụp được cả khi menu âm lượng mở; đổi output chuyển stream đang phát.
- Cortile khởi động không bật tiling; Ctrl+Alt+Shift+T bật/tắt được.
- `systemctl --user --failed` không có lỗi mới.

Chạy kiểm thử:

```bash
python -m unittest discover -s tests -v
```

Thông tin snapshot và kết quả thực thi trên máy nguồn được ghi ở [lần kiểm chứng hiện tại](validation.md).

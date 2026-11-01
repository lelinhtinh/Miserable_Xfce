# Đối chiếu snapshot trước reset — 02/11/2026

## Nguồn đối chiếu

- Home read-only: `/var/lib/miserable-xfce/home-snapshots/20261101-230308/bwin`.
- Root Snapper **651**: `/.snapshots/651/snapshot`.
- Bản sao ngay trước reset vanilla: `~/.local/state/miserable-xfce/vanilla-backups/20261101-231603/`.
- Repo trước lượt đối chiếu: commit `d990b2d2` trên `main`.

Đã đọc snapshot bằng quyền quản trị, trích riêng cấu hình desktop/hardware vào `.build/operations/snapshot-audit/private/` có quyền 0700 và bị Git ignore. Đã so sánh file, symlink, kênh xfconf theo từng property sau khi chuẩn hoá đường dẫn home; kiểm tra launcher/autostart, unit và script đích. Báo cáo máy đọc được ở `file-diff.json`, `xfconf-final.json` trong cùng thư mục audit; bản xuất chi tiết phục vụ kiểm chứng cục bộ.

Phạm vi gồm XFCE/GTK, widget, phím tắt, autostart, bộ gõ, ứng dụng mặc định và các tích hợp GPU/audio đi cùng desktop. Tên thư mục cấu hình ứng dụng đã được kiểm kê để nhận diện phần liên quan; dữ liệu tài khoản/trình duyệt, mã nguồn công việc và nội dung tài liệu không phải cấu hình desktop để đóng gói vào fork.

## Kết quả và phần đã bổ sung

| Nhóm | Trong snapshot | Kết quả trong mã nguồn |
| --- | --- | --- |
| Phím tắt | 92 property có giá trị trong kênh keyboard-shortcuts, gồm Ctrl+Alt+M/P | Khớp sau khi chuẩn hoá home; hai phím chuyển màn hình đã sửa ở commit trước. |
| Window manager | 80 property XFWM, theme/compositing/workspace/phím quản lý cửa sổ | Khớp. |
| XFCE còn lại | Terminal, xsettings, power manager, session, keyboard, Thunar | Các property có tác dụng đã khớp; action Open Terminal Here được bổ sung trong `home/.config/Thunar/uca.xml`. |
| Hình nền | Một workspace nền chung; DP-4 có ảnh riêng, HDMI-0 còn ảnh mặc định XFCE | Bổ sung single-workspace-mode/number. Hình nền lấy từ TOML cho cổng đang connected, panel theo Primary; không chép tên cổng/layout cố định vào xfconf. |
| Widget | Sidebar/System Stats/lịch, Data, ping, thời tiết, MPRIS, quick actions | Không thấy chức năng đang được tham chiếu bị mất. Khác biệt còn lại là cấu hình hoá, sửa launcher/daemon và định dạng. |
| Bộ gõ | Fcitx5 + Lotus, Ctrl+Alt+Space, US/Lotus, Super Smooth | Bổ sung profile/config/Lotus options, module GTK/Qt, `.xprofile`, environment.d và autostart. Các file cá nhân đã có được giữ khi cài lại. |
| Login màn hình | Autostart gọi script trong Documents để chọn DP-4, tắt HDMI-0 | Chuyển vào `start-session.sh`, đọc `display.physical_at_login`; tắt launcher cũ để không chạy trùng/phụ thuộc đường dẫn ngoài repo. |
| Màn hình ảo | Xorg NVIDIA + EDID giả 128 byte | Bổ sung template và EDID, render theo BusID/tên đầu ra trong TOML. Áp dụng riêng qua `render_restore.py`. |
| PulseAudio/Bluetooth | GStreamer whitelist + registry riêng | Bổ sung drop-in tương ứng trong bộ dựng cấu hình; không đổi audio provider qua apply desktop. |
| PipeWire | WirePlumber chạy `video-only` để PulseAudio quản lý audio | Bổ sung drop-in và hướng dẫn chọn stack tương ứng trên máy đích. |
| DAC Simgot | Unit đặt PCM của card GEW1 thành 100% | Bổ sung unit dựng theo `alsa_card`/`alsa_control`, bỏ qua khi card không có. |
| Lotus server | Enabled service theo user, stdout/stderr null | Bổ sung bước enable và drop-in cho tên tài khoản đích, không mang tên user nguồn. |
| Autostart ứng dụng | ChatGPT và Zalo | Bổ sung launcher có TryExec, giữ lệnh gốc. Không cài ứng dụng thay người dùng. |
| Bookmark | Gitlab/Github/Retro/Music trên `/mnt/data` | Bổ sung file GTK bookmarks; chỉnh qua Thunar/file và giữ bản cá nhân khi cài lại. |
| Ứng dụng mặc định | MIME/URI handler Chrome, ứng dụng công việc | Bổ sung `mimeapps.list`, giữ bản cá nhân khi cài lại; tài liệu chỉ rõ phụ thuộc app trên máy đích. |
| Flameshot | X11 legacy capture, contrastOpacity 188, startupLaunch | Đã có và khớp; không cần thêm bản sao. |
| Bốn dịch vụ desktop | Các unit từng enable ở default.target | Giữ bản sửa static/autostart sau DISPLAY đã kiểm chứng sau reboot, không khôi phục lỗi thứ tự khởi động. |

Sau bổ sung, 11 kênh xfconf của repo khớp **249 property** của snapshot. Khác biệt còn lại ở các kênh có trong repo là lịch sử ứng dụng/tray và cách đặt hình nền/panel theo màn hình hiện tại. Ba kênh không chép là `displays` và trạng thái cửa sổ của Settings Editor/Settings Manager.

## Các khác biệt được xác nhận không cần đưa lại vào bộ cài

| Dữ liệu trong snapshot | Lý do |
| --- | --- |
| `known_applications`, `known-players`, tray known-items, recent Whisker | Lịch sử do ứng dụng tự tạo; không phải cấu hình chức năng hoặc danh sách app ghim. |
| `displays.xml`, desktop icon coordinates, kích thước cửa sổ Settings | Theo phần cứng hoặc trạng thái phiên; layout hiện tại vẫn nguyên trên máy nguồn. |
| Launcher panel 13–16 | Không được panel đang dùng tham chiếu; là launcher mặc định còn sót. |
| `xfce4/desktop/accels.scm`, `Thunar/accels.scm` | Chỉ có các dòng accelerator mặc định được comment, không có phím custom đang có hiệu lực. |
| `xfce4-screenshooter` preferences | Phím chụp và quick action đang gọi Flameshot; file cũ vẫn còn trên máy. |
| Gmail/Spotify helper cũ, battery/wifi/updates script, `archlinux.svg` | Không được giao diện widget hiện tại tham chiếu; MPRIS hiện dùng script media đang có trong repo. |
| Picom launcher/helper và Breeze GTK assets/xsettingsd | Picom launcher bị Hidden; XFWM compositing và Lavanda hiện là cấu hình dùng. Breeze/ocean là phần còn sót từ KDE, không ghi đè theme đang dùng. |
| `pulseaudio.desktop` user override | Chỉ thêm `NotShowIn=KDE`; không thay đổi hành vi XFCE, bản autostart package được dùng. |
| `/etc/pulse/default.pa`, daemon/system/client config | So với package cache không có sửa đổi cần mang sang. |
| Unikey options, Lotus cache/empty macro/keymap, notification Wayland-KDE | Profile đang chọn Lotus; các bảng không có entry, cache layout hoặc thông báo của DE khác. |
| WirePlumber USB soft-mixer rule | ALSA monitor không chạy khi dùng profile video-only; DAC hiện được xử lý bằng `amixer` trong unit riêng. Không mang thêm rule không có tác dụng trên stack này. |
| arch-update tray/timer override | Tên chương trình/unit cũ hiện không được cài trên máy; không có daemon tương ứng để áp dụng lịch 6 giờ. |
| llama-chat/autocomplete/embed units | Không được enable; thuộc ứng dụng/model ngoài desktop, còn nguyên trong snapshot và home hiện tại. |
| Fingerprint udev + kill-fprintd, helper quản trị hệ thống trong `/usr/local/bin` | Thuộc cấu hình thiết bị/hệ thống riêng; fingerprint đang có cảnh báo thiếu module từ trước reset. Không tái tạo workaround lỗi như cấu hình desktop mặc định. Cần snapshot hệ thống nếu phục hồi đầy đủ máy nguồn. |
| Dconf, keyring, PulseAudio cookies và trạng thái thiết bị/app | Giữ trên máy hiện tại; không chép cơ sở dữ liệu tài khoản/trạng thái sang máy khác. Các tuỳ chọn giao diện tương ứng được quản lý qua xfconf/GTK trong repo. |

## Kiểm chứng

- **14 kiểm thử đạt**, gồm giữ cấu hình cá nhân và `.xprofile` qua cài lại/rollback; chuyển màn hình với cổng tuỳ chỉnh và lỗi bật cổng; dựng phần cứng theo lựa chọn; cài bundle vào home tạm bằng tài khoản đích mô phỏng, backup file và không dùng user nguồn.
- `systemd-analyze --user verify` xác nhận unit DAC được dựng hợp lệ; shell/XML và diff checks đạt.
- Bộ cấu hình mặc định dựng đủ 6 file, EDID có checksum hợp lệ. SHA-256 EDID: `fd4cf52c9d535a092e82cc83c8a280b02df0efad697b2866940c7ae7b0c6cd78`.
- Lượt này không chạy bundle cài phần cứng lên máy hiện tại hoặc reboot thêm; đây là đối chiếu snapshot, bổ sung nguồn và kiểm tra cài đặt trên staging. Kết quả reboot thật trước đó ở [validation.md](validation.md).

Cách sửa giá trị cá nhân và áp dụng trên máy đích: [settings.md](settings.md), [restore.md](restore.md).

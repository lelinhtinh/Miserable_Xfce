# Các tuỳ chỉnh bổ sung từ snapshot

Kết quả đối chiếu và các phần chủ động bỏ qua nằm ở [báo cáo snapshot](snapshot-audit.md). Không tạo profile mới; cấu hình desktop dùng trực tiếp `home/`. Cấu hình cần quyền root hoặc phụ thuộc phần cứng được dựng riêng từ `config/restore/`.

## Bộ gõ và ứng dụng tự khởi động

Bộ cài thêm Fcitx5, các module GTK/Qt và công cụ cấu hình vào danh sách package. Máy nguồn dùng **fcitx5-lotus-bin 6.0.4-1**, engine `lotus`, chế độ `Uinput (Super Smooth)`, phím bật/tắt **Ctrl+Alt+Space**. Lotus là phụ thuộc bổ sung ngoài danh sách pacman chính; cài Lotus theo [hướng dẫn của dự án](https://github.com/LotusInputMethod/fcitx5-lotus#cài-đặt--hướng-dẫn-sử-dụng) trước khi khôi phục dịch vụ server.

- `~/.config/fcitx5/config`: phím tắt và trạng thái bộ gõ dùng chung giữa ứng dụng.
- `~/.config/fcitx5/profile`: nhóm US + Lotus, Lotus mặc định.
- `~/.config/fcitx5/conf/lotus.conf`: chế độ gõ và các tuỳ chọn Lotus; cũng có thể sửa bằng GUI Fcitx5.
- `~/.xprofile`: installer ghép một block có đánh dấu để đặt biến môi trường X11, giữ nội dung khác và không lặp block khi cài lại. GTK 3/4 có `gtk-im-module=fcitx`; `environment.d/im.conf` giữ XMODIFIERS cho user manager.
- `fcitx5-xfce.desktop` khởi động Fcitx5 trong XFCE; file `org.fcitx.Fcitx5.desktop` Hidden ngăn launcher trùng từ cấu hình KDE cũ.
- ChatGPT và Zalo được giữ trong autostart, có `TryExec`; chỉ khởi động khi ứng dụng đã được cài. Installer desktop không cài hai ứng dụng này.

Khi cài lại, file cấu hình Fcitx5, MIME, bookmark và custom action Thunar đã có được giữ nguyên. Để dùng lại giá trị trong repo thay cho tuỳ chỉnh trên máy đích, sao lưu rồi di chuyển đúng file cấu hình đó ra ngoài trước khi chạy apply. Các file mới do installer tạo vẫn nằm trong manifest backup/rollback.

## Bookmark và ứng dụng mặc định

`~/.config/gtk-3.0/bookmarks` chứa ba đường dẫn của máy nguồn: `/mnt/data/Gitlab`, `/mnt/data/Github`, `/mnt/data/Retro/Music`. Sửa bằng sidebar Thunar hoặc file này cho phù hợp máy mới; đường dẫn trong file dùng URI `file://`, khoảng trắng là `%20`.

`~/.config/mimeapps.list` giữ lựa chọn Chrome/HTTP(S) và các handler ứng dụng từng dùng. Điều chỉnh file này hoặc GUI Default Applications nếu máy đích không cài những ứng dụng tương ứng. `~/.config/Thunar/uca.xml` giữ hành động Open Terminal Here.

## Màn hình thật và màn hình ảo NVIDIA

`[display]` trong `settings.toml` có thêm:

```toml
physical_at_login = true
nvidia_bus_id = "PCI:1:0:0"
nvidia_physical = "DFP-5"
nvidia_virtual = "DFP-0"
```

`physical_at_login` đưa phiên về màn hình thật qua script chuyển màn hình đã cấu hình. Bước này nằm trong `start-session.sh` trước configure/widget; autostart `rustdesk-virtual-display.desktop` cũ được tắt để không phụ thuộc script nằm trong Documents của máy nguồn. Đặt `false` để giữ bố cục hiện tại khi đăng nhập. Phiên X11 đang chạy phải có cổng đích connected; lỗi chọn cổng được ghi log và không chặn các dịch vụ desktop khác.

Xorg của máy nguồn dùng NVIDIA, ép nhận hai đầu ra DFP-5/DFP-0 và EDID giả cho HDMI-0. File EDID **128 byte** được lấy từ snapshot, không tải lại từ mạng. `nvidia_bus_id` dùng dạng `PCI:bus:device:function` với các số thập phân, phải khớp GPU trong `lspci`; tên DFP là tên của NVIDIA, khác tên cổng mà `xrandr` hiển thị. Máy dùng GPU/driver khác đặt `restore.nvidia_virtual_display=false` và tự cung cấp một màn hình ảo phù hợp trước khi dùng Ctrl+Alt+M/P.

## Âm thanh và lựa chọn khôi phục

Máy nguồn dùng **PulseAudio thật** cho âm thanh; PipeWire/WirePlumber giữ camera/chia sẻ màn hình. Đo bằng `LC_ALL=C pactl info`: `Server Name: pulseaudio`. Cấu hình này khác máy dùng `PulseAudio (on PipeWire ...)`. Máy nguồn còn có GStreamer 1.28.8, gst-plugins-base/good/bad/ugly, libldac 2.0.2.6 và pulseaudio-bluetooth 17.0+r134; cần các plugin codec tương ứng nếu muốn giữ khả năng Bluetooth như máy nguồn.

```toml
[restore]
nvidia_virtual_display = true
lotus_server = true
pulse_codec_filter = true
wireplumber_video_only = true
dac_volume = true
alsa_card = "GEW1"
alsa_control = "PCM"
```

| Khoá | Dữ liệu được dựng |
| --- | --- |
| `nvidia_virtual_display` | Xorg NVIDIA và EDID giả trong `/usr/share/rustdesk-virtual-display/`. |
| `lotus_server` | Enable `fcitx5-lotus-server@<tài khoản đích>.service`, giữ tuỳ chỉnh tắt stdout/stderr của server. Không hardcode tên tài khoản máy nguồn. |
| `pulse_codec_filter` | Drop-in GStreamer chỉ nạp coreelements/app/openaptx/ldac cho PulseAudio, cache registry riêng. |
| `wireplumber_video_only` | Drop-in chạy WirePlumber với profile `video-only`, tránh tranh quyền điều khiển audio với PulseAudio. |
| `dac_volume` | Service đặt mixer phần cứng USB DAC ở 100%; bỏ qua nếu card chưa xuất hiện trong `/proc/asound`. Không đặt âm lượng ứng dụng/PulseAudio thành 100%. |
| `alsa_card`, `alsa_control` | Tên card/control từ `aplay -l`, `amixer -c GEW1 scontrols`; ví dụ `GEW1` và `PCM`. Hiện nhận tên đơn gồm chữ/số/`_`/`-`. |

Nếu muốn giữ audio stack PipeWire của máy đích, đặt `pulse_codec_filter=false`, `wireplumber_video_only=false`; chọn `dac_volume` theo phần cứng thật. Nếu muốn dùng đúng stack của máy nguồn, chuẩn bị PulseAudio/PulseAudio Bluetooth/ALSA, PipeWire, WirePlumber và `alsa-utils` trước; không giữ provider `pipewire-pulse`. Việc chọn hoặc thay audio provider là bước quản trị riêng, không nằm trong apply desktop.

## Dựng và áp dụng trên máy đích

Chạy từ thư mục repo, bằng tài khoản desktop thường. Sửa TOML trước; giá trị mặc định trong mã nguồn mô tả máy nguồn.

```bash
python scripts/render_restore.py --target .build/restore-config
# Hoặc --config ~/.config/eww/settings.toml nếu đã thêm [restore] vào file cá nhân.
# Xem các file được dựng và install.sh trước khi thực hiện.
bash .build/restore-config/install.sh
```

Lệnh đầu chỉ dựng file trong một thư mục mới/rỗng, không ghi cấu hình đang dùng. Các khoá không có trong `[restore]` được coi là false. File TOML cá nhân cũ được installer giữ nguyên, vì vậy cần bổ sung section này nếu muốn dùng nó để dựng cấu hình.

`install.sh` kiểm tra phụ thuộc và GPU NVIDIA đúng PCI trước khi ghi. File user được cài vào `$HOME` của tài khoản đang chạy; file hệ thống dùng `sudo install` để có owner root. File bị thay có backup đánh số `.~1~`, `.~2~`… bên cạnh. Script enable dịch vụ cho lần đăng nhập/boot tiếp theo, không restart display manager/audio hoặc tự reboot. Các cờ false chỉ bỏ qua việc cài mới, không xoá cấu hình từng cài trước đó.

Với bộ lựa chọn mặc định, renderer tạo **6 file cấu hình** cùng manifest SHA-256 và script cài. Giữ lại bộ file đã dựng và các backup để đối chiếu/hoàn tác trên máy đích. Sau khi áp dụng, đăng nhập lại hoặc reboot khi thuận tiện rồi kiểm tra bộ gõ, cổng màn hình và audio server.

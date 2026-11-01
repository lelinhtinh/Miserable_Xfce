# Kiểm chứng ngày 01/11/2026

## Snapshot trước thay đổi

- Root Snapper: **#651**, `/.snapshots/651/snapshot`.
- Home read-only: `/var/lib/miserable-xfce/home-snapshots/20261101-230308`.
- Repo trước dọn: `/mnt/data/Backups/Miserable_Xfce/20261101-230308/source-before-cleanup.tar.gz`, kèm SHA-256 và danh sách package.
- Hồ sơ snapshot: `/var/lib/miserable-xfce/latest-snapshot`.

Root/home là hai subvolume trên `/dev/sdb2`; repo nằm trên ext4 `/dev/sdb4`. Cả ba phần đã được sao lưu trước khi xoá resource.

## Trạng thái kiểm chứng

Đã chuyển cấu hình trực tiếp về `home/`, bỏ profile riêng, chỉ giữ resource đang tham chiếu. **10 kiểm thử đạt**: cài lại giữ file TOML, Data có khoảng trắng/không tồn tại, toạ độ không hợp lệ, thời tiết đọc config/cache đúng, backup/rollback, launcher/XML, đồ thị asset GTK và cập nhật xfconf qua D-Bus cô lập.

Eww, Skippy/Chipmunk và plugin PulseAudio đã build lại thành công. Bộ cài thu gọn đã được áp dụng vào home tạm; daemon Eww, nhãn Data và theme Rofi đã được kiểm tra. Bộ icon Numix đang dùng được lấy ở bước build.

Bộ XFCE mặc định đã được cài bằng pacman theo danh sách CachyOS. KDE/Plasma và `cachyos-kde-settings` đã vắng mặt từ trước nên bước gỡ được ghi nhận là không cần thực hiện lại.

Đã đưa phiên desktop thật về cấu hình mặc định: theme **Adwaita**, icon **elementary**, hai panel ID 1/2 từ `/etc/xdg/xfce4/panel/default.xml`. Bản sao cấu hình trước reset: `~/.local/state/miserable-xfce/vanilla-backups/20261101-231603/`.

Các vấn đề đã được phát hiện và sửa qua thực thi:

- Bỏ `xfce4-datetime-plugin` khỏi danh sách lỗi thời; chức năng đã hợp nhất vào Clock của panel.
- Bỏ yêu cầu trực tiếp `zlib`, tránh xung đột với `zlib-ng-compat` của CachyOS; dùng provider mà GTK/libpng đã yêu cầu.
- Cho `xfsettingsd --replace` chạy nền thay vì chờ tiến trình daemon.

## Kết quả áp dụng lại trên desktop thật

- Cài phụ thuộc thành công; build bằng Rust 1.99.1, CMake 4.4.5, Meson 1.12.1 và Ninja hệ thống. `zlib-ng-compat` được giữ nguyên.
- Đã áp dụng `home/` và công cụ đã dựng lên tài khoản thật sau bước vanilla. Theme Lavanda-Dark-Compact-Tokyonight, icon Numix-Circle, WM Miserable-Chrome, XFWM compositing bật, panel ID 2 cao 46 px.
- Hình nền được đặt cho các workspace trên cổng màn hình hiện có; không cần chép `displays.xml` của máy nguồn.
- `cortile`, `skippy-overview`, `miserable-sidebar-anchor`, `whisker-win-key` đều active; `systemctl --user --failed` trả 0 unit lỗi.
- Mở System Stats thật: Data đọc 768,5 GiB từ filesystem đã cấu hình. Mở Sidebar thật: địa điểm lấy từ TOML và API thời tiết trả dữ liệu. Đã đóng các cửa sổ widget sau kiểm tra.
- Chỉnh xuống dòng nhãn đĩa để tránh cắt chữ, và dùng cơ chế daemonize gốc của Eww + `ping` thay cho phụ thuộc tên process; daemon tiếp tục trả `pong` qua các lần chạy lệnh riêng biệt.
- 10 kiểm thử tự động đạt; kiểm tra cú pháp/diff không có lỗi.

## Kiểm tra sau reboot ngày 02/11/2026

Đã reboot thật và đăng nhập qua LightDM vào XFCE X11 lúc 00:12. Boot ID đổi từ `0a2b2768-dc6a-4c8e-aa1b-ffff197b53fe` sang `71b0a436-b8e8-479b-9c66-4de9057003b9`.

- LightDM enabled/active; không có system hoặc user unit ở trạng thái failed.
- Theme Lavanda, icon Numix-Circle, WM Miserable-Chrome, compositing và panel 46 px được giữ sau đăng nhập. Hình nền đúng trên DP-4/HDMI-0; font Overpass/Feather được tìm thấy.
- System Stats và Sidebar mở thành công; Eww trả `pong`. Data đọc 768,5 GiB, thời tiết Hoà Xuân, Đà Nẵng trả 25,2°C. Đã đóng widget sau kiểm tra.
- Journal phát hiện các symlink `default.target.wants` cũ làm bốn dịch vụ chạy trước khi có DISPLAY. Các unit nay là static, được XFCE autostart gọi sau khi import môi trường X11; script đăng nhập gỡ symlink cũ của đúng bốn unit này. Đã áp dụng bản sửa trên máy và chạy lại autostart: cả bốn active, `NRestarts=0`, không còn nằm trong dependency của `default.target`. Bản sửa thứ tự khởi động được kiểm tra trong phiên hiện tại, chưa reboot thêm.
- 10 kiểm thử đạt; `systemd-analyze --user verify` xác nhận bốn unit hợp lệ.
- Cảnh báo thiếu `pam_fprintd.so` cũng có trong journal của boot trước; đây là cấu hình xác thực vân tay của máy, chưa thay đổi. Portal GTK của tài khoản đang dùng active.

Báo cáo chi tiết và bản sao trước sửa nằm trong `.build/operations/reboot-check/` (không đưa vào Git). Phần cứng trên máy CachyOS thứ hai vẫn cần kiểm tra ở máy đích.

## Khôi phục phím tắt chuyển màn hình

Bản sao trước reset có Ctrl+Alt+M/P gọi `toggle-rustdesk-display`; cấu hình đưa vào repo đã bỏ sót hai binding này. Đã khôi phục trực tiếp qua xfconf, đưa script vào `home/.local/bin/` và bổ sung `[display]` trong file TOML cùng tài liệu. Script cũ trên máy vẫn còn trước khi sửa; đây là lỗi mất binding khi reset/apply, không phải driver mất sau reboot.

11 kiểm thử đạt, gồm mô phỏng chuyển cả hai chiều với cổng tuỳ chỉnh, không tắt màn hình đang dùng nếu bật cổng đích lỗi hoặc cổng đích disconnected. Đã kiểm tra binding thật và hai cổng DP-4/HDMI-0 đang connected. Chưa kích hoạt chuyển cổng trên phiên đang làm việc trong lượt sửa này.

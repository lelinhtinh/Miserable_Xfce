# Kiểm chứng ngày 01/11/2026

## Snapshot trước thay đổi

- Root Snapper: **#651**, `/.snapshots/651/snapshot`.
- Home read-only: `/var/lib/miserable-xfce/home-snapshots/20261101-230308`.
- Repo trước dọn: `/mnt/data/Backups/Miserable_Xfce/20261101-230308/source-before-cleanup.tar.gz`, kèm SHA-256 và danh sách package.
- Hồ sơ snapshot: `/var/lib/miserable-xfce/latest-snapshot`.

Root/home là hai subvolume trên `/dev/sdb2`; repo nằm trên ext4 `/dev/sdb4`. Cả ba phần đã được sao lưu trước khi xoá resource.

## Trạng thái kiểm chứng

Đã chuyển cấu hình trực tiếp về `home/`, bỏ profile riêng, chỉ giữ resource đang tham chiếu. **10 kiểm thử đạt**: cài lại giữ file TOML, Data có khoảng trắng/không tồn tại, toạ độ không hợp lệ, thời tiết đọc config/cache đúng, backup/rollback, launcher/XML, đồ thị asset GTK và cập nhật xfconf qua D-Bus cô lập.

Eww, Skippy/Chipmunk và plugin PulseAudio đã build lại thành công. Bộ cài thu gọn đã được áp dụng vào home tạm; daemon Eww, nhãn Data và theme Rofi đã được kiểm tra. `home/` khoảng 5,1 MB và `vendor/` khoảng 4,4 MB; bộ icon Numix đang dùng được lấy ở bước build.

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

Không reboot hoặc đăng xuất phiên đang làm việc. Đăng nhập LightDM sau reboot và phần cứng trên máy CachyOS thứ hai vẫn cần kiểm tra ở máy đích. Các cửa sổ ứng dụng đang mở được giữ nguyên trong lần kiểm chứng này.

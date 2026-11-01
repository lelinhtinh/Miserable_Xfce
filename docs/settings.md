# Tuỳ chỉnh cá nhân

File cấu hình chính là **`~/.config/eww/settings.toml`** sau khi cài; giá trị ban đầu nằm ở `home/.config/eww/settings.toml` trong repo. Đây là TOML, không phải shell: không cần escape khoảng trắng trong đường dẫn. Không nhập mật khẩu/token vào file này.

```toml
[storage]
data_path = "/mnt/data"
data_label = "Data"
sidebar_path = "~"

[weather]
location = "Hoà Xuân, Đà Nẵng"
latitude = 16.00495
longitude = 108.22045
timezone = "Asia/Ho_Chi_Minh"
refresh_seconds = 900

[network]
ping_host = "1.1.1.1"

[desktop]
wallpaper = "~/.local/share/backgrounds/desinight_by_smn_paike.png"
panel_height = 46
browser = "google-chrome"
terminal = "xfce4-terminal"
pinned_apps = ["com.microsoft.VSCode", "xfce4-terminal", "google-chrome"]
store_command = ["pamac-manager"]

[display]
physical_output = "DP-4"
virtual_output = "HDMI-0"
virtual_mode = "1920x1080"
virtual_rate = "60"
```

| Khoá | Ý nghĩa |
| --- | --- |
| `storage.data_path` | Thư mục thuộc filesystem muốn đo ở System Stats. Hỗ trợ `~` và đường dẫn có khoảng trắng. Đo dung lượng của filesystem chứa thư mục này, không cộng kích thước từng file. Thư mục không tồn tại thì hiển thị `—`, không lấy nhầm filesystem khác. |
| `storage.data_label` | Nhãn của ô Data trong System Stats. |
| `storage.sidebar_path` | Thư mục muốn đo dung lượng còn trống trong Sidebar. |
| `weather.location` | Tên địa điểm hiển thị; thay tên không tự tìm toạ độ. |
| `weather.latitude`, `longitude` | Toạ độ dùng gọi Open-Meteo; vĩ độ −90…90, kinh độ −180…180. Không cần API key. |
| `weather.timezone` | Múi giờ IANA, ví dụ `Asia/Ho_Chi_Minh`, `Asia/Tokyo`. Dùng cho API và thời gian cập nhật. |
| `weather.refresh_seconds` | Thời gian cache API 60…86400 giây. Widget đọc config mỗi phút; đổi toạ độ/múi giờ tạo cache riêng. |
| `network.ping_host` | IP hoặc hostname đo độ trễ; không được bắt đầu bằng `-`. |
| `desktop.wallpaper` | File hình nền áp dụng cho các màn hình/workspace khi cấu hình hoặc đăng nhập. Đặt `""` nếu muốn quản lý hình nền bằng Desktop Settings. |
| `desktop.panel_height` | Chiều cao panel 20…128 pixel; sidebar lấy chiều cao panel thật để neo vị trí. |
| `desktop.browser`, `terminal` | Tên helper Xfce trong `/usr/share/xfce4/helpers/`; không kèm đuôi `.desktop`. Ứng dụng cần được cài sẵn. |
| `desktop.pinned_apps` | Desktop ID ghim ở Docklike, không kèm `.desktop`. |
| `display.physical_output`, `virtual_output` | Tên cổng thật/ảo từ `xrandr --query`. Hai cổng phải khác nhau; cổng ảo phải được hệ thống cung cấp sẵn. |
| `display.physical_at_login` | Chọn màn hình thật trước khi khởi động widget ở lần đăng nhập; mặc định true. |
| `display.virtual_mode`, `virtual_rate` | Độ phân giải/tần số có sẵn trên cổng ảo, mặc định `1920x1080` và `60`. |
| `desktop.store_command` | Mảng lệnh và đối số mở Software Manager, ví dụ `["pamac-manager"]`, `["bauh"]`. Không diễn giải shell. |

Kiểm tra cú pháp/giá trị trước khi áp dụng:

```bash
python ~/.config/eww/scripts/settings.py
```

Data và Sidebar đọc lại các giá trị khi poll tiếp theo. Bấm nút làm mới trong ô thời tiết để cập nhật ngay địa điểm mới. Sau khi đổi browser, ứng dụng ghim hoặc chiều cao panel:

```bash
python ~/.local/share/miserable-xfce/configure.py --restart-panel
```

Hình nền trong TOML được áp dụng khi đăng nhập và khi chạy lệnh configure ở trên. Nếu muốn tự chọn hình bằng Desktop Settings của XFCE, đặt `desktop.wallpaper = ""` để giao quyền quản lý cho XFCE.

Để thử config khác mà không sửa file đang dùng, các script widget nhận biến môi trường `MISERABLE_CONFIG=/đường/dẫn/settings.toml`. File cá nhân đã có được giữ nguyên khi chạy lại installer; muốn đổi giá trị mặc định cho các máy sau, sửa file TOML trong mã nguồn.

## Chuyển màn hình thật/ảo

- **Ctrl+Alt+M**: chuyển qua lại giữa màn hình thật và màn hình ảo.
- **Ctrl+Alt+P**: chuyển về màn hình thật.

Script `~/.local/bin/toggle-rustdesk-display` đọc `[display]` mỗi lần chạy. Máy khác cần đổi tên cổng theo `xrandr --query`; script không tự tạo màn hình ảo hoặc cài driver RustDesk. Nếu file TOML cũ chưa có `[display]`, các giá trị mặc định ở trên được dùng. Script kiểm tra cổng đích đang connected và bật cổng đích thành công trước khi tắt cổng còn lại. Nhật ký: `${XDG_RUNTIME_DIR}/display-toggle-${UID}.log`.

## Bộ gõ, bookmark và cấu hình phần cứng

Các file cấu hình Fcitx5, MIME và bookmark cũng là cấu hình cá nhân; installer giữ file đang có khi cài lại. Sửa bằng GUI tương ứng hoặc file riêng được liệt kê trong [restore.md](restore.md). `.xprofile` được ghép block Fcitx5, giữ nội dung khác.

Các trường `display.nvidia_bus_id`, `nvidia_physical`, `nvidia_virtual` và section `[restore]` chỉ dùng khi dựng cấu hình phần cứng bằng `scripts/render_restore.py`. Danh sách khoá, điều kiện audio/GPU và cách áp dụng nằm ở [hướng dẫn khôi phục](restore.md). Nếu TOML cá nhân cũ chưa có các trường mới, bổ sung từ file mẫu trong repo trước khi dùng bước dựng riêng.

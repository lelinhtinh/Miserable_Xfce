# Tuỳ chỉnh cá nhân

File duy nhất cần sửa là **`~/.config/eww/settings.toml`** sau khi cài; giá trị ban đầu nằm ở `home/.config/eww/settings.toml` trong repo. Đây là TOML, không phải shell: không cần escape khoảng trắng trong đường dẫn. Không nhập mật khẩu/token vào file này.

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

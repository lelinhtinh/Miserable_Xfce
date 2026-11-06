# Miserable Xfce — CachyOS

Bản fork của [mehedirm6244/Miserable_Xfce](https://github.com/mehedirm6244/Miserable_Xfce), cập nhật trực tiếp theo desktop hiện tại. Chỉ có một bộ cấu hình trong `home/`; các theme, icon, hình nền và widget cũ không còn dùng đã được bỏ.

**[Cài đặt / kiểm chứng trên CachyOS](docs/setup.md)** · **[Tuỳ chỉnh cá nhân](docs/settings.md)**

Tùy chọn phần cứng: [vân tay USB ELAN, Fingwit và màn hình đăng nhập LightDM](docs/fingerprint.md).

```bash
bash scripts/installer.sh --snapshot
bash scripts/installer.sh --baseline
bash scripts/installer.sh --build
```

Đăng xuất XFCE, vào TTY bằng tài khoản thường rồi chạy:

```bash
bash scripts/installer.sh --apply
```

Hoặc áp dụng vào phiên XFCE đang chạy sau khi đã tạo snapshot:

```bash
python scripts/session.py baseline
python scripts/session.py apply
```

Cấu hình cá nhân nằm ở `~/.config/eww/settings.toml`: thư mục Data, địa điểm thời tiết, địa chỉ ping, hình nền, chiều cao panel, ứng dụng ghim và Software Manager. Cài lại không ghi đè file này nếu đã có.

```bash
python -m unittest discover -s tests -v
```

Cảm ơn dự án gốc của mehedirm6244, phần installer của G-flame và các đóng góp upstream. Các nguồn dùng để build được cố định trong `config/sources.lock.json`; bản vá nằm trong `patches/`, các gói nguồn/release cần thiết nằm trong `vendor/`. Phụ thuộc icon được lấy từ Numix; không lưu các bộ icon khác không dùng.

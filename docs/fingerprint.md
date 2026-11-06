# Vân tay ELAN và màn hình LightDM

Bộ sửa này dành riêng cho cảm biến USB **04f3:0c3d**, firmware 1.65, ảnh 144×64 trên máy nguồn CachyOS. Đây là bước cài thêm có chủ đích; `installer.sh --apply` không tự đổi driver hay xác thực. Repo chỉ giữ mã nguồn, bản vá và cấu hình; mỗi người tự đăng ký vân tay trên máy đích.

## Driver và bộ so khớp

Driver chính thức nhận sai kiểu cảm biến và NBIS không so khớp được các mẫu thử. Bản vá dùng nhánh [SIGFM của libfprint](https://github.com/goodix-fp-linux-dev/libfprint) tại commit trong `config/sources.lock.json`, bổ sung luồng chụp ELAN dạng chạm. Thu 12 khung, lấy trung bình 3 khung cuối và chuẩn hóa tuyến tính ở kích thước gốc. SIGFM dùng ngưỡng 100 và đăng ký 15 mẫu. ID riêng `elan-sigfm` tách mẫu khỏi driver chính thức.

Chuẩn bị `base-devel git meson ninja pkgconf glib2 libgusb opencv fprintd` trên CachyOS bằng một lần nâng cấp toàn hệ thống nếu thiếu. Build bằng tài khoản thường:

```bash
bash scripts/build_fingerprint.sh
sudo bash scripts/install_fingerprint.sh
```

Build lấy source cố định, kiểm checksum doctest v2.4.12 (giấy phép MIT trong header), áp dụng patch và chạy bốn nhóm kiểm tra gốc. Thư viện chỉ được cài riêng tại `/usr/local/lib/elan-0c3d-sigfm/`; drop-in systemd cho riêng fprintd dùng thư viện này. Script cài lưu file cũ vào thư mục riêng chỉ root truy cập trong `/var/backups/`, rồi khởi động lại fprintd. Không sửa PAM hoặc đăng ký hiện có.

Máy nguồn đã có `pam_fprintd` trong cấu hình xác thực và có mật khẩu dự phòng. Máy mới cần kiểm tra cấu hình PAM của distro trước khi dùng vân tay đăng nhập; bộ cài này không tự thêm luật PAM dùng chung cho mọi máy.

Đăng ký **chỉ một ngón** cho cả lượt, nhấc hẳn tay giữa các lần chạm. Giữ ngón giữa cảm biến khoảng hai giây khi xác thực:

```bash
fprintd-enroll -f right-index-finger "$USER"
fprintd-verify -f right-index-finger "$USER"
```

[Fingwit](https://github.com/linuxmint/fingwit) là GUI đăng ký/xóa vân tay qua fprintd. Máy nguồn đã cài và mở được Fingwit 1.1.1-2 từ AUR, hiển thị cảm biến và ngón đã lưu. Mục bật/tắt xác thực của phiên bản này dùng `pam-auth-update` của Debian, không phù hợp CachyOS; dùng cấu hình PAM của distro. Việc nhận vân tay không cung cấp mật khẩu để giải mã GNOME Keyring: keyring vẫn có thể hỏi mật khẩu ở lần đăng nhập đầu.

Để trở về thư viện chính thức, dừng fprintd, di chuyển riêng `/etc/systemd/system/fprintd.service.d/60-elan-0c3d-sigfm.conf` ra ngoài, chạy `systemctl daemon-reload` rồi khởi động fprintd. Mẫu SIGFM còn được giữ dưới ID riêng. Nếu đã có bản tùy chỉnh trước khi cài, khôi phục file từ thư mục backup được script in ra. Cập nhật OpenCV/fprintd có thể cần build lại thư viện.

## Tự vào phiên sau khi xác thực

GTK greeter 2.0.9 chỉ tự vào phiên nếu đã hiện lời nhắc mật khẩu. PAM vân tay có thể thành công mà không hiện lời nhắc, khiến người dùng phải bấm Login. Bản vá `patches/lightdm-gtk-greeter.patch` thêm tùy chọn `start-session-on-authentication-success=true`. Greeter chỉ vào phiên sau khi LightDM báo xác thực thành công; xác thực thất bại hoặc bị hủy không mở phiên.

Chuẩn bị phụ thuộc trong `config/lightdm/PKGBUILD`, gồm `xfce4-dev-tools gobject-introspection gettext intltool` và các phụ thuộc runtime liệt kê trong file. Sau đó:

```bash
bash scripts/build_greeter.sh
sudo pacman -U .build/lightdm-package/lightdm-gtk-greeter-1:2.0.9-2.2-x86_64.pkg.tar.zst
sudo bash scripts/install_greeter_appearance.sh "$USER" \
  "$HOME/.local/share/backgrounds/desinight_by_smn_paike.png" "$HOME/.face"
```

Thay hai đường dẫn ảnh bằng file thật trên máy. Script chép ảnh nền và avatar vào `/usr/local/share/lightdm/assets/` để tài khoản lightdm đọc được, gọi AccountsService đặt avatar, rồi cài drop-in greeter. Home vẫn giữ quyền riêng tư. Script lưu cấu hình và đường dẫn icon cũ trong `/var/backups/lightdm-appearance.*`; không restart LightDM. Drop-in dùng chung ảnh nền cho các tài khoản; avatar áp dụng cho tài khoản được truyền vào.

Bản vá được đóng thành gói cùng tên `lightdm-gtk-greeter`, vì LightDM đang chạy đã ghi nhớ tên greeter. Lần mở greeter tiếp theo dùng binary mới mà không cần dừng phiên hiện tại. Đăng xuất hoặc reboot khi thuận tiện để kiểm tra toàn bộ lần đăng nhập. Nâng cấp distro có thể thay gói tùy chỉnh; build lại bản vá nếu cần.

Để hoàn tác, cài lại gói `lightdm-gtk-greeter` chính thức từ cache/repository, bỏ drop-in `70-fingerprint-appearance.conf` hoặc khôi phục bản cũ từ backup. Khôi phục ảnh cũ nếu có và gọi AccountsService `SetIconFile` với đường dẫn icon đã lưu (chuỗi rỗng chọn avatar mặc định). Không cần restart LightDM trong lúc đang làm việc.

## Kết quả ngày 06/11/2026

- Bốn nhóm unit test driver đạt: `sigfm`, `fpi-device`, `fpi-ssm`, `fpi-assembling`.
- Ngón đã đăng ký khớp 4/5 lần; ngón giữa trái chưa đăng ký bị từ chối cả 5/5 lần. Đây là mẫu kiểm tra nhỏ, không đo tỷ lệ nhận nhầm tổng quát.
- PAM service `lightdm` trả thành công sau khi cài thư viện lâu dài.
- Bảy trường hợp callback xác thực greeter đạt, kiểm tra trực tiếp hàm trích từ source đã vá. Build greeter tự chạy lại kiểm tra này.
- LightDM cô lập bằng `--test-mode`/Xephyr: chạm ngón trỏ phải, không bấm Login/Unlock; xác thực thành công và greeter tự yêu cầu phiên `xfce` ngay sau đó ở mốc +3,93 giây. Avatar và ảnh nền hiển thị đúng. Harness đầu thiếu phiên giả mang tên xfce nên kết quả xác nhận yêu cầu mở phiên, chưa phải một lần đăng nhập XFCE thật hoàn chỉnh.
- Gói đã cài trên máy nguồn: `lightdm-gtk-greeter 1:2.0.9-2.2`, pacman kiểm tra 260 file và không có file bị thay. Không đăng xuất, restart LightDM hoặc reboot phiên đang làm việc.

Ảnh chụp cảm biến, template đăng ký, điểm so khớp từng mẫu, avatar cá nhân và log phiên thử được giữ ngoài repo. Không dùng chung mẫu đăng ký giữa các máy.

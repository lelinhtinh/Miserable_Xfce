# Tự mở GNOME Keyring bằng TPM

Bộ mở này giữ nguyên mật khẩu và file keyring mã hóa. Người dùng đăng nhập LightDM bằng vân tay; trước khi chạy các ứng dụng XFCE, `.xprofile` gọi dịch vụ mở keyring. Dịch vụ lấy bí mật từ credential đã mã hóa bằng **TPM 2.0 + khóa host của systemd**, rồi chuyển cho GNOME Keyring qua phiên Secret Service **DH/AES**. Không ghi mật khẩu rõ ra file, dòng lệnh hay journal; không thay đổi PAM, Secure Boot hoặc cấu hình boot.

Đây là tích hợp riêng cho LightDM/GNOME Keyring, có dùng phương thức nội bộ `UnlockWithMasterPassword` của GNOME Keyring. Cần kiểm tra lại sau nâng cấp lớn GNOME Keyring/systemd. Nguồn tham khảo: [systemd credentials](https://systemd.io/CREDENTIALS/), [systemd-creds](https://www.freedesktop.org/software/systemd/man/latest/systemd-creds.html), [mã xử lý mở keyring của GNOME](https://gitlab.gnome.org/GNOME/gnome-keyring/-/blob/51.1/daemon/dbus/gkd-secret-service.c).

## Cài đặt và tạo credential

Yêu cầu: TPM 2.0 sử dụng được tại `/dev/tpmrm0`, systemd có hỗ trợ encrypted credentials, GNOME Keyring, libsecret có introspection, python-gobject và Zenity. Máy nguồn dùng systemd 262.1, gnome-keyring 51.1 trên CachyOS; đã có đủ các phụ thuộc này.

```bash
sudo bash scripts/install_keyring_tpm.sh "$USER"
/usr/local/libexec/miserable-keyring-tpm enroll
```

Lệnh thứ hai chạy bằng tài khoản desktop thường, trong phiên LightDM cục bộ đang active. Hộp thoại yêu cầu mật khẩu hiện tại của keyring. Mật khẩu được kiểm tra trên bản sao file keyring trong thư mục tmpfs riêng và một D-Bus/daemon cô lập; không khóa hoặc sửa keyring của phiên đang làm việc. Nếu nhiều keyring dùng cùng mật khẩu, chỉ cần nhập một lần; nếu khác nhau, công cụ hỏi riêng. Mật khẩu trống bị từ chối.

Sau khi kiểm tra, công cụ yêu cầu xác thực quản trị để seal credential, giải mã đối chiếu trong bộ nhớ, rồi mới thay credential cũ và thêm block vào `~/.xprofile`. Sao lưu `.xprofile` tại `~/.local/state/miserable-keyring-tpm/`; file hệ thống cũ được lưu trong `/var/backups/miserable-keyring-tpm.*`. Credential cũ khi enroll lại được lưu riêng dưới `/var/backups/keyring-tpm-*`, chỉ root truy cập.

Các đường dẫn được tạo, với UID của tài khoản đích:

- `/usr/local/libexec/miserable-keyring-tpm`: helper root-owned.
- `/etc/credstore.encrypted/miserable-keyring-UID.cred`: chỉ chứa ciphertext, root-owned, mode 600.
- `/etc/systemd/system/miserable-keyring-tpm-UID.service`: oneshot chạy dưới UID người dùng. `LoadCredentialEncrypted=` cấp dữ liệu đã giải mã trong vùng credential runtime của systemd; dữ liệu này không được ghi vào file cấu hình. Service kết thúc sẽ dọn vùng runtime đó.
- `/etc/polkit-1/rules.d/49-miserable-keyring-tpm-UID.rules`: chỉ cho tài khoản tương ứng ở phiên cục bộ active gọi **start đúng unit này**. Không cấp quyền quản trị unit khác hoặc giải mã tùy ý.
- Block `MISERABLE KEYRING TPM` trong `.xprofile`: gọi dịch vụ đồng bộ trước các ứng dụng X11. Không enable dịch vụ ở boot hoặc mở keyring trước đăng nhập.

Helper kiểm tra qua logind rằng UID có phiên cục bộ active, loại user/X11 hoặc Wayland, service LightDM. Nó kiểm tra UID trong credential và mở đúng các collection đã đăng ký, bao gồm trường hợp tồn tại cả `Login` và `login`. Không đổi alias, chuyển dữ liệu hay tạo keyring mới.

## Chính sách TPM và giới hạn

Credential được seal bằng `--with-key=host+tpm2 --tpm2-pcrs=4+7`, không có fallback sang khóa host đơn thuần hoặc khóa null. Cần cả TPM gốc, khóa host `/var/lib/systemd/credential.secret` và PCR phù hợp để mở. PCR 4 gắn với phép đo mã boot; PCR 7 gắn với chính sách Secure Boot.

Máy nguồn đang **tắt Secure Boot** và không boot bằng measured UKI. Vì vậy, đây không phải chuỗi boot đã được xác minh: cơ chế giữ mã hóa và ràng buộc với TPM, nhưng không bảo đảm chống người có quyền sửa hệ điều hành trên chính máy đó. Nó cũng không chứng minh vân tay trực tiếp bên trong TPM; LightDM/PAM xác thực người dùng, sau đó dịch vụ mở keyring. Tiến trình có quyền của người dùng trong phiên đã mở vẫn có thể đọc các bí mật được GNOME Keyring cung cấp.

Thay bootloader, Secure Boot, firmware hoặc cấu hình boot có thể đổi PCR và làm tự mở thất bại. Khi đó vẫn nhập mật khẩu keyring bình thường, rồi chạy lại `enroll` nếu tin cậy trạng thái boot mới. Đổi mật khẩu keyring cũng cần enroll lại. Không xóa/reset TPM để xử lý lỗi này. Nếu TPM/credential không dùng được, bước `.xprofile` ghi thông báo chung vào journal và tiếp tục đăng nhập; ứng dụng dùng hộp thoại mật khẩu keyring thông thường.

## Kiểm tra và tắt

```bash
systemctl --no-ask-password start "miserable-keyring-tpm-$(id -u).service"
journalctl -u "miserable-keyring-tpm-$(id -u).service" -n 10
python -m unittest discover -s tests -v
```

Service là oneshot và có thể bị systemd thu hồi trạng thái khi đã kết thúc; journal ghi kết quả từng lượt. Kiểm thử tự động dùng keyring tạm trên D-Bus riêng: xác thực đúng/sai, kiểm tra bản sao mã hóa, từ chối credential sai UID/mật khẩu trống và chặn đọc credential nếu thiếu phiên hợp lệ. Không cần TPM để chạy các kiểm thử này.

Tắt hook mà vẫn giữ credential:

```bash
/usr/local/libexec/miserable-keyring-tpm disable
```

Gỡ cấu hình và chuyển credential mã hóa vào backup root-only:

```bash
sudo bash scripts/uninstall_keyring_tpm.sh "$USER"
```

Không xóa file trong `~/.local/share/keyrings/`. Việc tắt bộ mở TPM không đổi mật khẩu hoặc xóa mật khẩu ứng dụng đã lưu. Cài lại bằng installer rồi enroll lại khi cần.

## Kiểm chứng trên máy nguồn ngày 07/11/2026

- Đã enroll hai collection `Login` và `login` của UID 1000; giữ nguyên file và mật khẩu keyring.
- Đối chiếu giải mã credential thành công, kiểm tra owner root/mode 600 và khóa host chỉ root truy cập.
- Đưa chính bí mật được TPM giải mã qua pipeline trong bộ nhớ vào daemon cô lập; cả hai bản sao keyring mã hóa đều mở được qua Secret Service DH/AES.
- Ciphertext bị sửa bị từ chối, không xuất plaintext. Hai file keyring gốc vẫn ở định dạng binary mã hóa, mode 600.
- Dịch vụ chạy trên phiên thật: `Keyrings ready: 2; unlocked: 1`, sau đó kiểm tra D-Bus xác nhận cả hai keyring không còn khóa. Lượt chạy lại thành công với `unlocked: 0`.
- Kiểm thử giao thức trên D-Bus riêng xác nhận mật khẩu sai bị từ chối và kiểm tra bản sao không khóa keyring gốc. Kiểm thử hook xác nhận cài lặp không nhân đôi block và tắt hook giữ cấu hình khác.
- Bước triển khai TPM không sửa `/etc/pam.d/system-auth` hoặc `/etc/pam.d/lightdm`; sau đó timeout vân tay được tăng riêng lên 60 giây theo [cấu hình vân tay](fingerprint.md). Không restart LightDM hoặc đăng xuất phiên đang làm việc. Cần kiểm tra trọn lượt đăng nhập vân tay ở lần đăng nhập bình thường tiếp theo.
- Bộ 20 kiểm thử đạt, gồm 16 kiểm thử desktop và 4 kiểm thử TPM keyring/hook đăng nhập. Credential thật, mật khẩu và file keyring không được đưa vào Git.

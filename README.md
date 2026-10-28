# INTERSTELLAR

Ứng dụng điều khiển thiên hà bằng cử chỉ tay, sử dụng **Python, OpenCV, MediaPipe và TouchDesigner**. Di chuyển bàn tay để điều khiển hiệu ứng, chụm ngón để thu nhỏ và snap để đổi màu bạc, vàng cam, tím.

## Demo

<a href="https://www.youtube.com/watch?v=MjlHcUTJ6_g"><strong> Xem demo trên YouTube</strong></a>


## Cài đặt và chạy

**Yêu cầu:** Windows 10/11, webcam, [Python 3.12 64-bit](https://www.python.org/downloads/windows/) và [TouchDesigner 2025.33230](https://derivative.ca/download/archive). (hoặc TouchDesigner Non-Commercial)

Tải **Code → Download ZIP** rồi giải nén, hoặc dùng Git:

```powershell
git clone https://github.com/lunathewanderer/interstellar-mediapipe.git
cd interstellar-mediapipe
```

1. Nhấp đúp **`Install.bat`** để tạo môi trường, cài thư viện, tải mô hình và kiểm thử.
2. Nhấp đúp **`CreateProject.bat`**. Mở TouchDesigner → **Dialogs → Textport**, nhấn **Ctrl + V → Enter** để tạo mạng hiệu ứng.
3. Chọn **File → Save As**, lưu tên **`GalaxyHands.toe`** trong cùng thư mục với `main.py`.
4. Nhấp đúp **`Run.bat`**, hoặc chạy:

```powershell
python main.py
```

Các lần sau chỉ cần bước 4. Mô hình được tải từ Google khi cài đặt; tệp `.toe` được tạo riêng trên từng máy. Nếu chưa có `.toe`, chương trình mở preview camera với hiệu ứng cơ bản.

## Điều khiển

| Thao tác | Hiệu ứng |
|---|---|
| Di chuyển lòng bàn tay | Di chuyển tâm thiên hà |
| Chụm ngón cái và ngón trỏ (pinch) | Thu nhỏ thiên hà |
| Thả pinch | Mở rộng trở lại |
| Tách hoặc đưa hai tay gần nhau | Tăng hoặc giảm kích thước |
| Nghiêng đường nối hai tay | Thay đổi hướng |
| Chạm ngón cái với ngón giữa rồi tách nhanh (snap) | Đổi màu bạc → vàng cam → tím |
| Đưa tay ra khỏi camera | Hiệu ứng trôi nhẹ rồi mờ dần |

Để snap dễ nhận, giữ tiếp xúc khoảng **0,2 giây**, để ngón trỏ tách ra, rồi tách ngón giữa nhanh. Chờ khoảng **1 giây** giữa hai lần. Chương trình nhận chuyển động qua camera, không nghe tiếng búng tay.

**Phím tắt:** `C` đổi màu, `D` bật/tắt landmark, `R` reset, `+/-` đổi chất lượng, `Q/Esc` dừng tracker. Nhấp vào cửa sổ camera hoặc TouchDesigner trước khi dùng phím. Đóng TouchDesigner bình thường khi dùng xong.

## Cách hoạt động

**Camera → OpenCV → MediaPipe → Thuật toán Python → TouchDesigner**

MediaPipe cung cấp 21 landmark mỗi tay. Code chuẩn hóa khoảng cách, nhận pinch/snap, điều khiển một hoặc hai tay và áp dụng [One Euro Filter](https://gery.casiez.net/1euro/) để giảm rung. Python gửi ảnh cùng thông số qua bộ nhớ dùng chung; TouchDesigner dựng và ghép thiên hà lên camera. Hình ảnh được xử lý trên máy.

## Cấu trúc project

```text
main.py            Khởi chạy ứng dụng
app.py             Camera và suy luận MediaPipe
config.json        Ngưỡng nhận diện và chất lượng hiệu ứng
galaxy/            Cử chỉ, chuyển động, màu và truyền dữ liệu
touchdesigner/     Dựng mạng và các callback hiển thị
shaders/           Hiệu ứng thiên hà trên GPU
models/            Nguồn tải và mã kiểm tra mô hình
tools/             Tải mô hình và tạo lệnh thiết lập TouchDesigner
tests/             Kiểm thử logic và tích hợp
```

## Kiểm thử và xử lý lỗi

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

- **Camera không mở:** đóng Camera, Zoom hoặc Teams đang dùng webcam; kiểm tra quyền camera của ứng dụng desktop.
- **Chỉ thấy lõi sáng:** hoàn thành bước tạo và lưu `GalaxyHands.toe`.
- **Thiếu thư viện hoặc mô hình:** chạy lại `Install.bat`.
- **Hiệu ứng chậm:** nhấn `-` hoặc chạy `python main.py --quality low`.
- **Snap khó nhận:** bật `D` để xem trạng thái; dùng `C` để kiểm tra riêng chức năng đổi màu.

Tài liệu tham khảo: [MediaPipe Hand Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python), [TouchDesigner GLSL TOP](https://derivative.ca/UserGuide/Write_a_GLSL_TOP).

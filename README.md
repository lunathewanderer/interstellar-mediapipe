# INTERSTELLAR - Thiên hà tương tác bằng cử chỉ tay

Ứng dụng sử dụng **MediaPipe Hand Landmarker**, **OpenCV** và **TouchDesigner** để biến bàn tay thành bộ điều khiển một thiên hà ánh sáng trên hình ảnh webcam. Người dùng có thể di chuyển, thu phóng, xoay thiên hà và búng tay để đổi màu **bạc → vàng cam → tím**.

## Video demo

<p align="center">
  <a href="https://www.youtube.com/watch?v=MjlHcUTJ6_g">
    <img src="https://i.ytimg.com/vi/MjlHcUTJ6_g/maxresdefault.jpg" alt="Video demo Interstellar: điều khiển thiên hà bằng cử chỉ tay" width="900">
  </a>
</p>

<p align="center">
  <a href="https://www.youtube.com/watch?v=MjlHcUTJ6_g"><strong>▶ Xem demo trên YouTube</strong></a>
</p>

## Yêu cầu hệ thống

- Windows 10/11, 64-bit và webcam hoạt động bình thường.
- **Python 3.12, 64-bit**: [tải Python](https://www.python.org/downloads/windows/).
- **TouchDesigner 2025.33230** và GPU tương thích: [tải TouchDesigner](https://derivative.ca/download/archive). Có thể dùng bản Non-Commercial cho bài tập phi thương mại này.
- Có Internet khi cài thư viện và tải mô hình lần đầu. Sau đó, hình ảnh được xử lý trên máy.

## Cài đặt và khởi chạy

### 1. Tải project

Chọn **Code → Download ZIP** trên GitHub rồi giải nén, hoặc chạy:

```powershell
git clone https://github.com/lunathewanderer/interstellar-mediapipe.git
cd interstellar-mediapipe
```

### 2. Cài thư viện

Cài Python 3.12 và TouchDesigner trước, sau đó nhấp đúp **`Install.bat`**.

File này tạo môi trường `.venv`, cài các thư viện trong `requirements.txt`, tải mô hình Hand Landmarker từ Google và chạy bộ kiểm thử. Không cần tự tải mô hình hay cài MediaPipe vào Python bên trong TouchDesigner.

Cũng có thể chạy bằng PowerShell trong thư mục project:

```powershell
.\Install.bat
```

### 3. Tạo hiệu ứng TouchDesigner - chỉ làm một lần

1. Nhấp đúp **`CreateProject.bat`** để sao chép lệnh tạo project.
2. Mở TouchDesigner, chọn **Dialogs → Textport**, nhấn **Ctrl + V**, rồi **Enter**.
3. Chọn **File → Save As**, lưu tên **`GalaxyHands.toe`** trong cùng thư mục với `main.py`.

`GalaxyHands.toe` là tên tệp mà launcher sử dụng. Repository cung cấp script dựng mạng để mỗi máy tạo được tệp phù hợp với đường dẫn của mình.

### 4. Chạy ứng dụng

Nhấp đúp **`Run.bat`**, hoặc chạy:

```powershell
python main.py
```

Khi đã lưu `GalaxyHands.toe`, chương trình mở TouchDesigner và bắt đầu theo dõi tay. Nếu chưa có tệp này, chương trình mở bản xem trước camera với hiệu ứng cơ bản; hãy hoàn thành bước 3 để xem thiên hà đầy đủ.

## Hướng dẫn sử dụng

Đặt webcam ở nơi đủ sáng, đưa toàn bộ bàn tay vào khung hình và hạn chế để các ngón che nhau.

| Cử chỉ | Hiệu ứng |
|---|---|
| Di chuyển lòng bàn tay | Di chuyển tâm thiên hà |
| Chụm ngón cái và ngón trỏ | Thu nhỏ thiên hà về gần hai đầu ngón |
| Thả pinch | Thiên hà mở rộng trở lại |
| Đưa hai tay xa nhau hoặc gần nhau | Tăng hoặc giảm kích thước |
| Nghiêng đường nối hai tay | Thay đổi hướng thiên hà |
| Chạm ngón cái với ngón giữa, giữ ngắn rồi tách nhanh | Đổi màu bạc → vàng cam → tím |
| Đưa tay ra khỏi khung hình | Hiệu ứng giữ ngắn, trôi nhẹ rồi mờ dần |

**Cách snap dễ nhận:** giữ ngón cái chạm ngón giữa khoảng **0,2 giây**, để ngón trỏ tách ra, rồi búng/tách ngón giữa nhanh. Chờ khoảng **1 giây** giữa hai lần. Chương trình nhận chuyển động qua hình ảnh, không nghe tiếng búng tay; một thao tác quá nhanh có thể bị bỏ lỡ giữa các khung hình.

### Phím tắt

Nhấp vào cửa sổ camera hoặc cửa sổ TouchDesigner trước khi dùng phím.

| Phím | Chức năng |
|---|---|
| `C` | Đổi màu ánh sáng, giống sự kiện snap |
| `D` | Bật/tắt landmark và thông tin debug; quan sát `snap=READY` |
| `R` | Đặt lại theo dõi, mẫu sao và màu bạc |
| `+` / `=` | Tăng chất lượng |
| `-` | Giảm chất lượng |
| `Q` / `Esc` | Dừng theo dõi và giải phóng camera |

Sau khi dừng tracker, đóng TouchDesigner bình thường nếu đã dùng xong.

## Cách chương trình hoạt động

**Camera → OpenCV → MediaPipe → Thuật toán Python → TouchDesigner → Thiên hà tương tác**

- **MediaPipe** cung cấp 21 landmark trên mỗi bàn tay, tối đa hai tay.
- **Thuật toán của project** chuẩn hóa khoảng cách theo kích thước tay, làm mượt bằng One Euro Filter, nhận pinch bằng hai ngưỡng và thời gian duy trì, phát hiện snap qua chuỗi tiếp xúc rồi tách nhanh, và xử lý mất dấu.
- **TouchDesigner và GLSL** dựng sao, các nhánh xoắn, quỹ đạo, vệt sáng và bloom, rồi ghép lên hình ảnh camera.

Python là tiến trình mở camera. Ảnh và dữ liệu điều khiển được chuyển tới TouchDesigner qua bộ nhớ dùng chung trên Windows. Ứng dụng không tự ghi hình hoặc tải hình ảnh webcam lên mạng.

Xem giải thích chi tiết tại [ALGORITHMS.md](docs/ALGORITHMS.md).

## Cấu trúc chính

```text
interstellar-mediapipe/
├── main.py                 # Điểm khởi chạy
├── app.py                  # Camera và suy luận MediaPipe
├── config.json             # Ngưỡng nhận diện và cấu hình hiệu ứng
├── Install.bat             # Cài thư viện và tải mô hình
├── Run.bat                 # Mở ứng dụng
├── CreateProject.bat       # Tạo mạng TouchDesigner lần đầu
├── UpdateProject.bat       # Cập nhật mạng đã lưu khi source thay đổi
├── TestCamera.bat          # Kiểm tra camera và landmark
├── setup.ps1
├── requirements.txt
├── galaxy/                 # Theo dõi, cử chỉ, màu và truyền dữ liệu
├── touchdesigner/          # Script dựng mạng và callback
├── shaders/                # Hiệu ứng GPU
├── models/source.json      # Nguồn tải và mã kiểm tra mô hình
├── tests/                  # Kiểm thử logic
├── tools/                  # Công cụ cài đặt và kiểm tra
└── docs/                   # Thuật toán, thiết lập và xử lý lỗi
```

Các môi trường ảo, bộ cài, video, báo cáo nháp, bản sao lưu, dữ liệu runtime và tệp `.toe` tạo riêng trên từng máy không được đưa vào repository. Mô hình `.task` được tải tự động khi cài đặt.

## Kiểm thử và xử lý lỗi

Chạy kiểm thử logic và kiểm tra cấu trúc:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe tools/check_project.py
```

Project có **57 kiểm thử tự động** cho cử chỉ, chuyển động, truyền dữ liệu và launcher. Các kết quả đã ghi cùng phạm vi kiểm thử được trình bày trong [TEST_REPORT.md](docs/TEST_REPORT.md). Bộ kiểm thử tổng hợp không thay thế đánh giá tỷ lệ nhận đúng snap và độ trễ bằng webcam thực tế.

| Vấn đề | Cách xử lý |
|---|---|
| Camera không mở | Đóng Camera/Zoom/Teams; kiểm tra quyền truy cập camera của ứng dụng desktop |
| Thiếu thư viện hoặc mô hình | Chạy lại `Install.bat` |
| Chỉ thấy hiệu ứng lõi đơn giản | Tạo và lưu `GalaxyHands.toe` theo bước 3 |
| Snap khó nhận | Bật `D`, giữ tiếp xúc rõ hơn; dùng `C` để kiểm tra riêng chức năng đổi màu |
| Hiệu ứng chậm | Nhấn `-` hoặc chạy `python main.py --quality low` |
| Mạng TouchDesigner cũ sau khi sửa code | Chạy `UpdateProject.bat`, dán lệnh vào Textport rồi lưu lại |

Hướng dẫn bổ sung: [thiết lập TouchDesigner](docs/TOUCHDESIGNER.md), [xử lý lỗi](docs/TROUBLESHOOTING.md), [kiểm thử bằng tay](docs/MANUAL_TESTS.md).

## Tài liệu tham khảo

- [MediaPipe Hand Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python)
- [OpenCV](https://docs.opencv.org/4.x/)
- [TouchDesigner GLSL TOP](https://derivative.ca/UserGuide/Write_a_GLSL_TOP)
- [One Euro Filter](https://gery.casiez.net/1euro/)

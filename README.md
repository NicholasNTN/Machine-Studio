# MachineScope Studio v1.0.13 PRO UI + LIVE TIMELINE BETA

MachineScope Studio v1.0.13 — PRO UI + LIVE TIMELINE

MỤC TIÊU
Bản này tập trung sửa 7 feedback UI/Timeline của v1.0.12 và triển khai hướng giao diện PRO đã duyệt.

1) SỬA LỖI ẨN BASIC EDITOR LÀM PREVIEW TRÀN
- Exporter được đổi sang QSplitter dọc thật sự:
  TOP    = Cài đặt xuất + Preview + Lồng tiếng/Sub
  BOTTOM = Basic Video Editor
- Khi ẩn Editor, widget Editor được hide trong splitter và toàn bộ chiều cao trả về Preview.
- Không còn layout cũ giữ khoảng trống/geometry sai.
- Khi mở lại, chiều cao Editor trước đó được khôi phục.

2) TRIM/CUT ÁP DỤNG NGAY LÊN PREVIEW TIMELINE
- Timeline Editor trở thành nguồn thời gian chính khi "Dùng timeline khi Xuất Video" bật.
- Ví dụ source 01:06 trim còn 51.523s:
  Preview slider phía trên đổi ngay về 00:51.
- Không cần render lại video chỉ để xem trim.
- Player vẫn decode file gốc nhưng app ánh xạ source time <-> edited global time theo thời gian thực.
- Khi tới OUT của clip, playback tự chuyển clip kế tiếp.
- Clip cuối dừng đúng OUT.
- Final Export vẫn render timeline thật bằng FFmpeg.

3) ĐỒNG BỘ PLAYHEAD ĐỎ <-> SLIDER XANH
- Một global timeline clock duy nhất.
- Video chạy -> playhead đỏ chạy theo.
- Kéo slider xanh -> playhead đỏ đi cùng.
- Click/kéo ruler đỏ -> slider xanh + video seek theo.
- Click vào clip không kéo -> seek tới đúng thời điểm đó.
- Sửa geometry timeline: bỏ minimum-width/gap làm playhead lệch sau nhiều clip.

4) AI STUDIO — 40 PHONG CÁCH + NGHĨA TIẾNG VIỆT
Dropdown vẫn giữ 100% tên tiếng Anh để vừa dùng vừa học.
Ngay dưới dropdown có dòng "🇻🇳 Nghĩa" giải thích tiếng Việt.

Một số style mới:
- How it works
- Engineering breakdown
- Mega machines
- Manufacturing process
- Satisfying process
- Invention showcase
- Innovation story
- Product teardown
- Science and discovery
- History documentary
- News report
- Business case study
- Storytelling documentary
- Mystery and curiosity
- Top 10 countdown
- Educational lesson
- Beginner friendly
- Expert deep dive
- Cinematic narration
- High-energy shorts
- Agriculture and machinery
- Construction and heavy equipment
- Automotive engineering
- Aerospace engineering
- Technology innovation
- Environmental documentary
- Food production
- Travel documentary
- Human interest story
- Problem solution explainer
- Myth vs fact
- Data driven explainer
... tổng cộng 40 style.

Style và Market cũng được lưu trong Settings khi bấm Lưu Settings.

5) PREVIEW ZOOM IN / OUT
Header Preview có:
  [−] [100%] [+] [Fit]
- Range 50% -> 300%.
- Zoom chỉ ảnh hưởng editor canvas, KHÔNG làm thay đổi video xuất.
- Text/Sub/Logo/Blur/Image vẫn dùng đúng tọa độ % của video.
- Khi zoom > 100%: giữ chuột GIỮA và kéo để pan canvas.
- Fit đưa về 100% và reset pan.

6) PANEL RESIZE CHUYÊN NGHIỆP
- Cài đặt xuất | Preview | Lồng tiếng/Sub dùng QSplitter ngang.
- Preview | Basic Video Editor dùng QSplitter dọc.
- Kéo thanh phân cách để thay đổi chiều rộng/chiều cao.
- Splitter handle được làm rõ và highlight khi hover.
- Size panel được lưu trong Project/Autosave.
- Có nút:
  ☰ Cài đặt
  Lồng tiếng ☰
  để ẩn/hiện side panel, mở rộng Preview khi cần.

7) UI/UX COMPACT
- Log Export ẩn mặc định -> nút ▸ Log khi cần xem.
- Queue video giảm chiều cao.
- Layers trên Preview gọn hơn.
- Thuộc tính Text/Image (Content, Start, End, X/Y, Size, Font, Color, Opacity)
  ẩn mặc định -> ▸ Thuộc tính.
- Layer list vẫn giữ Add/Sửa/Xóa.
- Editor hint rút gọn thành 1 dòng workflow.
- Scrollbar + splitter styling mới.

PROJECT/AUTOSAVE LƯU THÊM
- preview_zoom_percent
- editor_visible
- editor_restore_sizes
- export_body_sizes
- export_vertical_sizes
- export_log_visible
- editor_layer_props_visible
- left_panel_visible
- right_panel_visible
- toàn bộ editor_clips/editor_layers của v1.0.12 vẫn giữ nguyên.

TEST NỘI BỘ
- Python AST/compile: PASS.
- Trim regression: source 66s -> timeline 51.523s: PASS.
- Multi-clip global/source time mapping: PASS.
- Static checks cho red/blue sync, splitters, zoom/pan, compact properties, 40 AI styles: PASS.

LƯU Ý TEST WINDOWS
Môi trường build không có PySide6 nên UI Qt thật trên Windows vẫn cần test thực tế.
Nếu có lỗi runtime, gửi popup + Crash/Log và version 1.0.13 để patch tiếp trên cùng codebase.


---

# MachineScope Studio v1.0.12 BASIC VIDEO EDITOR BETA

MachineScope Studio v1.0.12 — BASIC VIDEO EDITOR

EDITOR PANEL
- Nút: ✂ Video Editor / ✂ Ẩn Editor
- Editor ẩn mặc định để giao diện Video Exporter vẫn gọn.
- Checkbox: Dùng timeline khi Xuất Video.

VIDEO TIMELINE
- + Video: thêm 1 hoặc nhiều video trực tiếp vào timeline.
- + Từ danh sách trên: đưa video đang chọn trong batch queue vào timeline.
- Nhiều video được ghép theo thứ tự timeline.
- Kéo thân clip sang trái/phải để đổi thứ tự.
- Kéo mép vàng trái/phải để Trim IN / OUT.
- Trim là non-destructive, có thể kéo ngược ra để lấy lại phần video gốc.
- Split tại vị trí Preview/playhead.
- Xóa đoạn: sau Split, chọn segment rồi xóa.
- Đặt IN: xóa logic phần trước playhead.
- Đặt OUT: xóa logic phần sau playhead.
- Numeric IN/OUT cho chỉnh chính xác đến mili-giây.
- Zoom timeline.
- Playhead timeline.
- Playback đi qua OUT của clip và tự sang clip kế tiếp.
- Clip cuối dừng đúng OUT.
- Preview Timeline: render proxy nhẹ của toàn bộ trim/split/reorder/merge.

FINAL EXPORT
- Nếu "Dùng timeline khi Xuất Video" bật:
  1. render toàn bộ timeline đã edit;
  2. đưa timeline đã ghép qua Video Exporter;
  3. áp blur/logo/sub/text/image/audio;
  4. xuất MP4 cuối.
- Hỗ trợ clip nguồn khác resolution/aspect ratio.
- Timeline chuẩn hóa video + audio bằng FFmpeg concat filter.

LAYERS TRÊN PREVIEW
- Multiple Text layers.
- Multiple Image/Sticker/Logo layers.
- Subtitle hiện tại.
- Logo/Watermark hiện tại.
- Chữ phủ hiện tại.
- Multiple Blur zones.
- Layer list hỗ trợ Thêm / Sửa / Xóa.

MULTIPLE TEXT
- Nội dung.
- Font.
- Màu.
- X/Y.
- Cỡ chữ.
- Opacity.
- Start/End trên timeline.
- Kéo trực tiếp trên Preview.
- Kéo handle góc phải để resize.

MULTIPLE IMAGE
- PNG/JPG/JPEG/WebP/BMP.
- X/Y.
- Scale.
- Opacity.
- Start/End trên timeline.
- Kéo trực tiếp trên Preview.
- Kéo handle góc phải để resize.
- Final export dùng timed FFmpeg overlay.

SAVE PROJECT
- editor_clips
- source_start/source_end
- thứ tự clip
- editor_layers
- layer timing/geometry
- trạng thái "Dùng timeline khi xuất"
đều lưu trong Project/Autosave.

QUY TRÌNH KHUYẾN NGHỊ
Video thô
  -> Basic Video Editor: cắt/ghép/trim
  -> AI Studio
  -> Voice
  -> Subtitle
  -> Layer/Text/Logo/Blur
  -> Export

Nếu cắt/ghép video SAU khi đã tạo Voice/Sub thì voice/sub cũ có thể không còn đúng
timeline mới. Vì vậy nên hoàn thiện cấu trúc video trước bước AI/Voice.

TEST BUILD
- Render 3 video nguồn khác aspect ratio.
- Trim.
- Split + xóa segment.
- Reorder.
- Merge timeline.
- 2 text layers + 1 image layer.
- Final MP4 export.
- Timeline expected: 4.20s.
- Timeline rendered: 4.20s.
- Final output: ~4.20s.
- Python syntax: PASS.

CHƯA PHẢI FULL CAPCUT
v1.0.12 tập trung vào editor cơ bản. Chưa có:
- Transition giữa clip.
- Keyframe animation.
- Speed ramp.
- Crop/rotate riêng từng clip.
- Multi-track audio waveform.
- Undo/Redo history.
Các phần này có thể thêm theo version sau mà không đổi cấu trúc project hiện tại.


---

# MachineScope Studio v1.0.11 WORD POP SYNC BETA

MachineScope Studio v1.0.11 — WORD POP SYNC

NEW SUBTITLE EFFECT
Word Pop Sync

WHAT IT DOES
- Narration reaches word A -> only word A is visible.
- Word A disappears as word B begins.
- Every new word starts slightly smaller, pops to ~108%, then settles to 100%.
- Tiny fade-in/fade-out makes the hand-off between words smooth.
- Voice silence remains subtitle silence.

TIMING METHOD
- Uses the REAL generated TTS audio duration.
- Uses FFmpeg silencedetect to preserve actual pauses.
- Distributes individual words inside each audible speech interval.
- Longer words receive slightly more display time.
- Punctuation gets a small timing weight.
- Does not call another AI API and does not add a heavy speech recognizer.

UI
Effect:
  Word Pop Sync

Controls:
  Word Pop: 108%
  Pop smooth: 110 ms

Recommended:
  Word Pop 106-110%
  Pop smooth 90-130 ms
  Hide subtitle on voice pause: ON
  Pause >= 220 ms

MODE SWITCHING
- Select Word Pop Sync -> app automatically generates subtitle_word_pop_en.srt.
- Switch back to another effect -> app rebuilds normal phrase subtitle from
  the same voice_manifest when the current subtitle came from Word Pop Sync.

IMPORTANT
This is real voice-duration + silence-aware synchronization. Because Gemini/Piper
TTS do not provide phoneme/word timestamps in this workflow, exact word boundary
timing is estimated intelligently inside the real speech duration. It is much
closer to CapCut-style word captions than sentence timing without adding another
slow AI/ASR stage.


---

# MachineScope Studio v1.0.10 SUB ANIMATION + READY PREVIEW BETA

MachineScope Studio v1.0.10 — SUB ANIMATION + READY PREVIEW

1) SUBTITLE ẨN KHI VOICE NGHỈ
- Subtitle không còn fallback sang toàn bộ AI scene khi đã có SRT/voice timeline.
- Cue end dùng end-exclusive để chữ không bị lưu thêm ở ranh giới/gap.
- TTS chunk được phân tích bằng FFmpeg silencedetect.
- Khoảng im lặng thật >= 220ms mặc định tạo khoảng trống subtitle.
- Text được chia theo các speech interval; trong đoạn silence không có cue.
- Có tùy chọn:
    [x] Ẩn sub khi giọng nghỉ
    Khoảng nghỉ >= 220 ms
- Manifest cũ v1.0.9 cũng được retro-detect từ file voice khi bấm LẤY SUB KHỚP GIỌNG.

2) VIDEO HIỆN NGAY KHI CHỌN
- Khi chọn/add video, app trích một still frame ở ~0.05s.
- Still được cache tại preview_cache/stills.
- Live Preview hiện ảnh ngay; không cần nhấn Play.
- Play chỉ bắt đầu chuyển động/audio.
- Khi QVideoSink có frame thật, frame động thay thế still tự nhiên.

3) HIỆU ỨNG SUB KIỂU SHORT-FORM/CAPCUT-LIKE
Hiệu ứng:
- Không
- Pop
- Bounce
- Slide Up
- Fade
- Karaoke
- Typewriter

Thông số:
- Thời gian animation: 60–1200 ms
- Cường độ: 10–200%
- Màu Karaoke

Live Preview:
- Pop/Bounce/Slide/Fade/Typewriter/Karaoke được vẽ trực tiếp bằng Qt overlay.
- Không reload video khi đổi hiệu ứng.

Final Export:
- Hiệu ứng được ghi vào ASS và burn bằng FFmpeg/libass.
- Pop/Bounce/Slide/Fade dùng ASS transform/move/fade.
- Karaoke dùng ASS karaoke timing.
- Typewriter tạo progressive ASS events.
- Vị trí/font/outline/background hiện tại vẫn được giữ.

LƯU Ý
- Đây là hiệu ứng tương tự workflow subtitle short-form, không phải sao chép preset độc quyền của CapCut.
- Để subtitle silence-aware từ voice cũ: bấm lại LẤY SUB KHỚP GIỌNG.
- Để voice mới có speech_intervals ngay từ đầu: tạo voice lại bằng v1.0.10.


---

# MachineScope Studio v1.0.9 PIPER VOICE MANAGER BETA

MachineScope Studio v1.0.9 — PIPER VOICE MANAGER

NEW TTS ENGINE
- Piper Offline (Free)
- Gemini TTS
- Edge TTS
- Windows SAPI

DEFAULT
Engine: Piper Offline (Free)
Voice: en_US-lessac-medium

PIPER VOICE MANAGER
- Search voice
- Filter language
- Refresh full online catalog from official Piper voices.json
- Shows downloaded/offline state
- Shows approximate download size when metadata is available
- Download only selected voice
- Listen/test downloaded voice
- Delete local voice
- Open MODEL_CARD / license page
- Double-click voice to select

OFFLINE FLOW
First use:
  Select Piper voice
  -> download .onnx + .onnx.json once
  -> model stored in MachineScope/piper_voices/

Next videos:
  -> no API request
  -> no TTS quota
  -> local ONNX synthesis

PERFORMANCE
- PiperVoice is cached in memory.
- Same voice is loaded once and reused across all video scenes.
- Speed maps to Piper length_scale.
- Output remains WAV and continues through the existing true-duration
  voice_manifest -> narration_synced.m4a -> subtitle_synced_en.srt pipeline.

LICENSE
- Voice models can have different licenses.
- Voice Manager does NOT guess commercial safety.
- "License / Model Card" opens the official model card for the selected voice.

INSTALL
- requirements.txt now includes piper-tts
- existing users can run install_piper.bat once


---

# MachineScope Studio v1.0.8 TTS FALLBACK BETA

MachineScope Studio v1.0.8 — TTS FALLBACK

NGUYÊN NHÂN LỖI
- AI hiểu video + viết kịch bản: CKEY -> HTTP 200, hoạt động tốt.
- Tạo giọng đọc: là pipeline riêng, vẫn dùng Gemini TTS + Google TTS API key.
- Google TTS key trả 429 => popup "Gemini báo 429".

SỬA
1. Tách rõ AI Provider và TTS:
   CKEY = hiểu video / viết script / dịch.
   Gemini TTS / Edge TTS / Windows SAPI = tạo voice.

2. Thêm:
   [x] Gemini lỗi → tự chuyển Edge TTS

3. Edge fallback mặc định:
   en-US-JennyNeural

4. Khi Gemini TTS trả:
   - 429
   - quota
   - rate limit
   - resource_exhausted
   app tự:
   - chuyển scene đang lỗi sang Edge TTS;
   - giữ Edge TTS cho toàn bộ scene còn lại;
   - tiếp tục build narration_synced.m4a;
   - tiếp tục tạo voice_manifest.json;
   - tiếp tục tạo subtitle_synced_en.srt;
   - không làm mất timeline đã tạo.

5. Nếu Google TTS key trống:
   - fallback ON => dùng Edge ngay.
   - fallback OFF => báo rõ cần Google TTS key.

6. Log TTS:
   selected engine
   selected voice
   scene hiện tại
   fallback reason
   final fallback voice

7. Mỗi item manifest lưu thêm:
   tts_engine
   tts_voice


---

# MachineScope Studio v1.0.7 CKEY DIAGNOSTICS BETA

MachineScope Studio v1.0.7 — CKEY DIAGNOSTICS

Sửa đúng lỗi chẩn đoán CKEY:
- worker_error ưu tiên AIProviderError trước GeminiError.
- Provider = CKEY không còn bị popup lấy nhầm thông báo Gemini từ traceback.

Mỗi request OpenAI-compatible giờ log:
[AI REQUEST]
- Provider
- POST endpoint
- Model
- Client Request ID
- Payload bytes
- Số frame ảnh

[AI RESPONSE]
- HTTP status
- Latency
- Request ID nếu gateway trả
- Input/output/total tokens nếu có usage
- Response bytes

[AI ERROR]
- HTTP status
- Latency
- Request ID
- Raw error body tối đa 4000 ký tự

429:
- AI Studio/Dịch Sub tự retry tối đa 2 lần.
- Test Provider retry 1 lần.
- dùng Retry-After nếu server gửi.
- nếu vẫn lỗi, popup ghi rõ CKEY HTTP 429 + raw response.
- không đổi provider thành Gemini trong thông báo.

Không log API key và không log base64 của frame.


---

# MachineScope Studio v1.0.6 MULTI AI + CKEY BETA

MachineScope Studio v1.0.6 — MULTI AI + CKEY

AI Provider:
○ Google Gemini
● CKEY
○ OpenAI
○ DeepSeek

CKEY defaults:
- API Key: sk-xxxxxxxx
- Base URL: https://api.xah.io/v1
- Model: levuphong2909/gemini-3.7-flash-high
- Endpoint: POST https://api.xah.io/v1/chat/completions

Routing:
- AI Studio: Provider đang chọn.
- Dịch Sub: Provider đang chọn.
- CKEY/OpenAI/DeepSeek: OpenAI-compatible Chat Completions.
- Google Gemini: giữ Google GenAI SDK.

Multimodal:
- CKEY/OpenAI-compatible fast analysis gửi frame dưới dạng
  image_url data:image/jpeg;base64,...
- Không còn hard-code model Gemini Flash-Lite khi Provider = CKEY.

TTS:
- Gemini TTS có Google TTS API Key riêng.
- Edge TTS / Windows SAPI không cần Google key.
- CKEY chat/completions không bị dùng nhầm làm TTS.

Secrets:
- Mỗi provider key lưu riêng trong Windows keyring.
- settings.json chỉ lưu provider/model/base URL, không lưu API key plaintext.


---

# MachineScope Studio v1.0.5 COOKIE-SAFE DOWNLOADER BETA

MachineScope Studio v1.0.5 — COOKIE-SAFE DOWNLOADER

Lỗi từ ảnh:
- Failed to decrypt with DPAPI
- Could not copy Chrome cookie database
- Firefox cookie profile/database không tồn tại

Cách sửa:
- Windows Auto không tự đọc browser cookies.
- Auto thử public/no-cookie + impersonation.
- Nếu có cookies.txt: dùng cookies.txt làm authenticated fallback.
- Edge/Chrome/Firefox/Brave chỉ chạy khi người dùng chọn rõ.
- Thêm ô Cookie file + nút Chọn cookies.txt.
- Preflight browser profile để không thử Firefox khi không cài/profile không tồn tại.
- DPAPI/DB lock/missing DB chuyển thành thông báo ngắn gọn.
- Cookie JSON bị từ chối sớm; yt-dlp cần Netscape cookies.txt.


---

# MachineScope Studio v1.0.3 INTERACTION + SUB FIT BETA

MachineScope Studio v1.0.3 — INTERACTION + SUB FIT

1) FIX + VÙNG THỦ CÔNG
Nguyên nhân chính xác:
QPushButton.clicked(bool) truyền False vào add_blur_zone(zone).
Code v1.0.2 gọi False.get(...) => AttributeError.

v1.0.3 sửa cả hai lớp:
- button dùng lambda, không truyền checked;
- add_blur_zone tự bỏ qua bool nếu bị gọi nhầm.

2) KHÓA CON LĂN THÔNG SỐ
Thêm "🔒 Khóa lăn thông số" — mặc định BẬT.
- Bật: wheel không bao giờ đổi SpinBox/DoubleSpinBox/ComboBox.
- Tắt: phải CLICK đúng ô trước rồi wheel mới hoạt động.
- Rời chuột khỏi ô / mất focus: tự disarm.
=> Scroll panel không còn làm X/Y/font/opacity nhảy ngoài ý muốn.

3) SNAP TRỤC X/Y
Blur, Subtitle, Logo, Chữ phủ:
- khi center tới gần X=50% => snap chính xác vào trục X;
- khi center tới gần Y=50% => snap chính xác vào trục Y;
- hiện guide xanh nét đứt khi đang snap;
- thả chuột thì guide biến mất.

4) SUBTITLE KHÔNG BỊ CẮT CHỮ
Không giảm font theo từng câu.
Thay vào đó:
- dùng QFontMetricsF đo độ rộng pixel THẬT của font hiện tại;
- tính đúng chiều rộng vùng subtitle;
- câu quá dài tự chia thành nhiều cue ngắn hơn;
- timeline con vẫn nằm trọn trong timeline voice;
- Live Preview có safety-net pixel split ngay cả với SRT project cũ;
- trước Final Export, SRT được pixel-reflow lần cuối.

Kết quả:
- 1 dòng;
- cùng cỡ font;
- không crop mất đầu/cuối chữ;
- không cần auto-shrink thô.


---

# MachineScope Studio v1.0.2 STABLE LAYOUT + EXPORT BETA

MachineScope Studio v1.0.2 — STABLE LAYOUT + EXPORT

- Fix Add Blur: thao tác + chỉ thêm vùng trước; cache/autosave chạy sau event click.
- Manual Blur độc lập với AUTO SUB.
- AUTO SUB được căn giữa, vùng mặc định gọn hơn.
- Subtitle mặc định "Căn giữa + bám Auto Blur".
- Sub X/Y/Width/Font được tính một lần từ Auto Blur; không đổi font theo từng câu.
- Câu dài được tách thành nhiều cue 1 dòng bằng fixed font.
- Lề trong configurable.
- SpinBox/DoubleSpinBox/ComboBox không nhận wheel nếu chưa click/focus.
- Export dùng runtime-check NVENC; fallback CPU khi GPU runtime không hoạt động.
- Export dùng file tạm + tên mới để tránh Windows lock/ghi đè.
- MP3 cover-art / data / subtitle side streams không được map vào output.
- Popup export ưu tiên hiển thị dòng lỗi thật thay vì chỉ Metadata.


---

# MachineScope Studio v1.0.1 ONE-LINE SUB BETA

MachineScope Studio v1.0.1 — ONE-LINE SUB

YÊU CẦU
Subtitle luôn chỉ hiển thị 1 dòng như video short/TikTok, không còn xếp 2–3 dòng.

CÁCH LÀM
1. Text dài KHÔNG bị ép xuống dòng.
2. App tự chia một câu TTS dài thành nhiều cue subtitle ngắn liên tiếp.
3. Các cue con vẫn nằm hoàn toàn bên trong start/end voice thật.
4. Thời lượng từng cue được chia tương đối theo lượng từ/ký tự.
5. Live Preview tự giảm font nếu một cue còn sát chiều rộng.
6. Final ASS render không tạo \N trong chế độ 1 dòng.

Ví dụ voice 4 giây:
"world's largest land machines, designed for heavy-duty earth moving"

Có thể thành:
00:01.00–00:02.20  world's largest land machines,
00:02.20–00:03.35  designed for heavy-duty
00:03.35–00:05.00  earth moving

Mỗi thời điểm chỉ có 1 dòng.

SETTING MỚI
- 1 dòng tự động: mặc định BẬT.
- Ký tự tối đa: mặc định 30.
- Font nhỏ nhất: mặc định 24.
- Độ rộng subtitle vẫn chỉnh bằng chuột/thông số.

DỊCH SUB
Sau khi Gemini dịch:
- giữ nguyên outer timeline của voice,
- tự reflow thành cue 1 dòng,
- không kéo subtitle dài hơn narration.

SRT IMPORT
- SRT được tự reflow theo 1 dòng nếu setting đang bật.
- ASS/SSA import giữ nguyên vì có style/timing riêng.


---

# MachineScope Studio v1.0 VIDEO SINK LIVE PREVIEW BETA

MachineScope Studio v1.0 — VIDEO SINK LIVE PREVIEW

NGUYÊN NHÂN TỪ LOG NGƯỜI DÙNG
- Video gốc đọc OK.
- processed_preview_0004.mp4 đọc OK.
- H.264/AAC streams đều hợp lệ.
- "Unknown cover type: 0x1" là warning metadata/container.
- h264_mf/hevc_mf là capability warning của Qt/Windows Media Foundation.
- Không có lỗi FFmpeg decode chính trong log được gửi.

LỖI KIẾN TRÚC V0.9
QVideoWidget trên Windows có thể dùng native video surface.
Các QWidget Blur/Sub/Logo đặt phía trên QVideoWidget không đảm bảo cùng compositing
surface, nên effect state thay đổi nhưng người dùng không thấy trên video.

V1.0 THAY HẲN PREVIEW ENGINE
QMediaPlayer
  -> QVideoSink
  -> QVideoFrame
  -> InteractivePreviewOverlay (1 QWidget duy nhất)

Widget này tự vẽ:
1. video frame
2. blur / black privacy mask
3. logo
4. chữ phủ
5. subtitle
6. selection handles

=> video và effect nằm trên CÙNG surface.

LIVE BLUR
- Đen mờ: vẽ alpha black trực tiếp trên frame.
- Trong mờ: crop đúng vùng nguồn -> downsample -> upscale để tạo blur real-time.
- Không cần FFmpeg render/reload chỉ để nhìn blur.
- AUTO SUB và Manual Blur đều thấy ngay khi bật.

LIVE SUB / LOGO / TEXT
- Subtitle thấy ngay.
- Logo thấy ngay.
- Chữ phủ thấy ngay.
- Kéo/resize bằng chuột trên cùng canvas.

KHÔNG RESET 00:00
- Chỉnh effect không đổi media source.
- Player tiếp tục ở position hiện tại.
- Background cache sau 4.2 giây chỉ dùng để kiểm tra final FFmpeg.
- Cache không tự thay Live Preview.

FINAL EXPORT
- Vẫn dùng FFmpeg pipeline của v0.9.
- Blur zones / Auto Sub / Subtitle / Logo / Text / Audio vẫn render thật.

LOG WARNING
- Unknown cover type: không phải lỗi.
- hevc_mf could not create MFT: Qt probing HEVC encoder capability, không ảnh hưởng H.264 source.


---

# MachineScope Studio v0.9 STABLE AUTO-BLUR BETA

MachineScope Studio v0.9 — STABLE AUTO-BLUR

1. SỬA LỖI APP TỰ TẮT
- Sửa vòng đời QThread: không còn xóa QThread ngay trong signal done/error.
- Worker chỉ được giải phóng sau signal finished của Qt.
- Áp dụng cho AI/TTS/Export, background preview và auto subtitle detector.
- Đây là lỗi có thể làm Windows/PySide abort toàn bộ process với thông báo kiểu:
  QThread: Destroyed while thread is still running.
- Final Export có preflight try/catch: lỗi setting/FFmpeg hiện popup, không làm app biến mất.
- Khi đóng app lúc worker đang chạy, app yêu cầu dừng/chờ worker sạch trước khi thoát.

2. CRASH LOG
- logs/crash.log: faulthandler + unhandled Python exception.
- logs/console.log: stdout/stderr/Qt/FFmpeg của toàn session.
- run.bat giữ cửa sổ lại nếu process thoát với exit code lỗi.
- open_crash_logs.bat mở hai file log.

3. AUTO CHE PHỤ ĐỀ GỐC
- Toggle: Tự động che phụ đề gốc có sẵn trên video.
- Dò local bằng OpenCV, không dùng API/AI và không upload video.
- Lấy mẫu nhiều frame, tìm band text-like ở nửa dưới video.
- Tạo một vùng riêng có nhãn AUTO SUB.
- AUTO SUB tự căn X/Y/W/H đủ che text + outline/shadow.
- Nếu detector không chắc chắn, dùng vùng fallback an toàn.
- AUTO SUB vẫn kéo/resize được bằng chuột hoặc nhập X/Y/W/H.

4. MANUAL BLUR RIÊNG
- Nút + Vùng thủ công tạo ngay một vùng mới, không bắt mở dialog.
- Mục đích: che logo có sẵn, watermark, biển số, khuôn mặt hoặc vùng khác.
- Kéo để di chuyển, kéo handle góc phải để resize.
- Có thể thêm nhiều vùng manual cùng AUTO SUB.
- Xóa AUTO SUB sẽ tắt chế độ tự che; xóa manual không ảnh hưởng AUTO SUB.

5. LOGO / CHỮ PHỦ CHỈNH BẰNG CHUỘT
- Logo: kéo để đổi vị trí, kéo handle để đổi kích thước.
- Chữ phủ: kéo để đổi vị trí, kéo handle để đổi cỡ chữ.
- Các giá trị X/Y/size được lưu Project và đi vào FFmpeg Final Export.
- Có panel thu gọn Thông số Logo / Thông số Chữ phủ.

6. LIVE PREVIEW MƯỢT
- Blur/Sub/Logo/Chữ phủ là Qt overlay trực tiếp, không reload QMediaPlayer.
- Vị trí phát hiện tại giữ nguyên, không quay về 00:00 khi chỉnh.
- Final-look cache vẫn render ngầm sau debounce.
- Background cache KHÔNG tự đổi file đang xem.
- Background FFmpeg chạy BELOW_NORMAL_PRIORITY trên Windows.
- Nếu NVENC có trong FFmpeg nhưng driver/CUDA thực tế không chạy được, app tự fallback CPU thay vì lỗi.
- Cache không chạy cạnh tranh lúc AI/TTS/Final Export đang chạy.

7. GIAO DIỆN GỌN
- Blur: panel ▸ Thông số vùng.
- Subtitle: panel ▸ Thông số phụ đề.
- Logo: panel ▸ Thông số Logo.
- Chữ phủ: panel ▸ Thông số Chữ phủ.
- Cột trái/phải vẫn scroll.

WORKFLOW BLUR MỚI
A. Che phụ đề gốc:
   bật Tự động che phụ đề gốc -> app dò -> AUTO SUB -> kéo nhẹ nếu cần.
B. Che logo/watermark khác:
   + Vùng thủ công -> kéo vùng lên logo -> resize.
C. Có thể dùng A + nhiều B đồng thời.


---

# MachineScope Studio v0.8 LIVE EDITOR BETA

MachineScope Studio v0.8 — LIVE EDITOR

MỤC TIÊU
- Chỉnh Blur/Sub bằng chuột ngay trên video.
- Không reload file video sau mỗi thay đổi.
- Không màn hình đen.
- Không nhảy về 00:00.
- Không làm giật playback vì render preview.
- Thông số chi tiết có thể ẩn/hiện để giao diện gọn.

1. LIVE OVERLAY EDITOR
Blur Zone:
- Click vùng blur để chọn.
- Kéo vùng để di chuyển.
- Kéo ô vuông góc phải để resize.
- Final render vẫn dùng FFmpeg blur thật.
- Live Preview dùng lớp edit trong suốt để thao tác ngay, không xử lý lại video frame.

Subtitle:
- Click subtitle để chọn.
- Kéo subtitle để đổi vị trí X/Y.
- Kéo ô vuông góc phải để đổi Độ rộng + Cỡ chữ.
- Thay đổi hiển thị trực tiếp trong lúc video đang chạy.
- Final ASS/SRT burn dùng X/Y/font/width đã chỉnh.

2. THÔNG SỐ THU GỌN
Blur:
- "▸ Thông số vùng"
- X / Y / W / H.
- Panel mặc định ẩn.

Subtitle:
- "▸ Thông số phụ đề"
- Preset / Font / Size / Color / Outline / X / Y / Width / Wrap...
- Panel mặc định ẩn.
- Có scroll ở cột trái/phải như trước.

3. LIVE MULTI-TRACK AUDIO
Không cần render video để nghe:
- source audio từ video
- narration/voice riêng
- background music riêng
- accompaniment/no-vocals riêng

Các track chạy song song và app tự sync mỗi ~350ms.
Khi tua video, các track audio cũng seek theo.
Khi Pause/Play, tất cả track Pause/Play cùng nhau.

=> chỉnh Voice volume / Music volume / Mute original không cần reload video.

4. BACKGROUND RENDER CACHE
- Sau khi ngừng chỉnh ~2.4 giây mới render cache.
- Render bằng NVENC RTX nếu FFmpeg có h264_nvenc.
- Nếu không có GPU encoder: x264 ultrafast chỉ 2 threads.
- Background render KHÔNG BAO GIỜ tự thay file đang xem.
- Xong chỉ hiện "✓ Render cache sẵn sàng".
- Chỉ khi người dùng chủ động bấm "✓ Xem bản render" thì mới đổi.
- Có nút "⚡ Live Preview" để quay lại source + live overlays/audio.

5. PLAYBACK
Trong lúc chỉnh:
- media player hiện tại không đổi source.
- position không reset.
- video không đen.
- timeline tiếp tục chạy.
- render cache không chiếm pipeline player.

6. FINAL EXPORT
Final render vẫn áp dụng thật:
- blur zones đúng X/Y/W/H
- subtitle đúng X/Y/size/width
- narration
- mute original/accompaniment
- music
- logo
- side background
- overlay text


---

# MachineScope Studio v0.7.2 BACKGROUND PREVIEW BETA

MachineScope Studio v0.7.2 — BACKGROUND PREVIEW

MỤC TIÊU
Không còn: thay một setting -> player reload -> video giật/đen/nhảy 00:00.

CƠ CHẾ MỚI

1. Debounce 1.4 giây
- Kéo slider / bật tắt nhiều setting liên tục:
  không render từng lần.
- App chờ bạn ngừng thao tác ~1.4s rồi render đúng trạng thái mới nhất.

2. Render NGẦM
- Current video/preview vẫn Play bình thường.
- FFmpeg tạo proxy mới bằng background worker riêng.
- Không dùng progress bar chính.
- Không ép QMediaPlayer reload khi render xong.

3. Khi render ngầm xong
Nếu video đang PLAY:
  - video tiếp tục chạy KHÔNG reload.
  - trạng thái: "✓ Preview mới sẵn sàng".
  - nút: "✓ Áp dụng Preview mới".

Nếu video đang PAUSE/STOP:
  - app tự áp dụng preview mới vì không làm gián đoạn playback.

4. Khi Pause
- Nếu đang có Preview mới chờ:
  app tự chuyển sang bản mới.
- Giữ gần đúng vị trí timeline đang xem.

5. Khi bấm Play
- Nếu có Preview mới chờ:
  app dùng bản mới rồi Play.

6. Nút Preview
- Không có preview mới: "↻ Render Preview ngầm".
- Đang render: "⏳ Rendering ngầm...".
- Render xong trong lúc đang xem: "✓ Áp dụng Preview mới".

7. Nếu thay setting trong lúc background render đang chạy
- Không spawn thêm nhiều FFmpeg.
- Đánh dấu dirty.
- Render xong bản hiện tại -> debounce -> render một lần nữa với state mới nhất.

KẾT QUẢ
Bạn có thể chỉnh Blur / Subtitle / Logo / Audio khi video vẫn đang chạy.
Màn hình không reload sau từng thao tác nữa.


---

# MachineScope Studio v0.7.1 PREVIEW PLAYER FIX BETA

MachineScope Studio v0.7.1 — PREVIEW PLAYER FIX

LỖI ĐÃ SỬA
- v0.7 luôn render Processed Preview đè vào cùng `processed_preview.mp4`.
- Qt Multimedia/Windows Media Foundation có thể cache URL hoặc giữ handle file cũ.
- Kết quả: trạng thái hiện Playing nhưng màn hình đen và timeline đứng 00:00.

CÁCH SỬA
1. Mỗi lần render tạo file mới:
   preview_cache/processed_preview_0001.mp4
   preview_cache/processed_preview_0002.mp4
   ...
2. Trước khi load preview:
   - player.stop()
   - setSource(empty)
   - chờ event-loop
   - load URL file mới.
3. Chỉ Auto Play sau khi Qt báo LoadedMedia/BufferedMedia.
4. Nếu Qt báo InvalidMedia/Error:
   - hiện trạng thái lỗi.
   - ghi lỗi vào Log.
5. FFprobe kiểm tra proxy vừa render trước khi đưa cho player.
6. Cleanup các proxy preview cũ sau khi Windows nhả file handle.
7. Nút Play tự reload media nếu player đang NoMedia/InvalidMedia.

TEST
- Bật Blur Zone → Cập nhật Preview.
- App render proxy mới.
- Preview phải tự chạy khi load xong.
- Timeline phải tăng khỏi 00:00.
- Blur/sub/voice phải xuất hiện trong Processed Preview.


---

# MachineScope Studio v0.7 SYNC + PROCESSED PREVIEW BETA

MachineScope Studio v0.7 — SYNC + PROCESSED PREVIEW FIX

FIX LÕI (không chỉ UI)

1. GIỌNG ĐỌC THỰC SỰ VÀO VIDEO
- TTS không còn gom nhiều scene thành chunk 30 giây.
- Tạo 1 voice file cho TỪNG scene AI.
- Voice được đặt chính xác vào start time của scene.
- Nếu câu đọc dài hơn scene, FFmpeg tự tăng tốc vừa đủ để không đè sang scene sau.
- Sau khi tạo voice, app tự bật "Tắt giọng gốc".
- Narration timeline có độ dài đúng bằng video.
- Final Export và Processed Preview dùng chính narration này.

2. SUBTITLE KHỚP VOICE THẬT
Khuyến nghị mới:
- KHÔNG tạo subtitle hoàn toàn mới bằng AI sau TTS.
- Text subtitle lấy từ CHÍNH script mà TTS vừa đọc.
- Timestamp subtitle lấy từ THỜI LƯỢNG AUDIO THẬT sau khi tạo voice/time-fit.
=> text và giọng là cùng một nguồn, timeline không còn dựa vào ước lượng AI ban đầu.

- "LẤY SUB KHỚP GIỌNG" chỉ hoạt động sau khi Tạo Giọng Đọc.
- English sub = exact English TTS script.
- Vietnamese sub = bản Việt AI nhưng dùng CHÍNH timestamp voice English.
- Dịch subtitle bằng Gemini chỉ thay text, GIỮ NGUYÊN timestamp 100%.

3. PROCESSED PREVIEW
Preview cũ chỉ phát source video, nên người dùng vẫn nghe giọng gốc và không thấy blur.
v0.7 thêm:
- "↻ Cập nhật Preview".
- Preview được FFmpeg render low-res qua CÙNG pipeline với Export:
  + voice narration
  + mute giọng gốc
  + source volume
  + background music
  + subtitle burn
  + blur zones
  + logo
  + nền 2 bên
  + chữ phủ
  + speed
- Sau Tạo Voice và Lấy Sub, app tự render Processed Preview.
- Blur/logo/audio/sub thay đổi sẽ schedule cập nhật preview.

4. BLUR ZONES
- Thêm/sửa vùng tự bật Blur.
- Preview render thật để nhìn thấy blur.
- Final Export dùng cùng blur config.

5. AI STUDIO
Giữ:
- Chọn Video.
- ← Video từ Exporter.
- AI hiểu + viết script.
- Auto-save project.

6. DỊCH THUẬT
- Bỏ ô Prompt tự do khỏi giao diện chính.
- Thay bằng Phong cách:
  + Tự nhiên - video US
  + Ngắn gọn - subtitle
  + Giữ thuật ngữ kỹ thuật
  + Sát nghĩa
- Dịch KHÔNG được sửa timestamps.

7. CAPCUT BRIDGE
Khôi phục:
- Xuất package.
- Mở CapCut.
Package có thể gồm:
- final export (nếu có)
- processed preview
- source video
- synced SRT
- narration
- nhạc
- accompaniment
- subtitle_style.json
- project.json

WORKFLOW CHUẨN v0.7

AI Studio
→ AI hiểu + viết kịch bản
→ Video Exporter / Tạo Giọng Đọc
→ app tự tắt giọng gốc + render Processed Preview
→ LẤY SUB KHỚP GIỌNG
→ chỉnh/dịch/style sub
→ Processed Preview
→ Xuất Video


## Cài đặt
1. Giải nén vào folder mới.
2. Chạy `install.bat`.
3. Chạy `run.bat`.
4. Settings → Gemini API → Test Gemini.
5. Nếu muốn tách vocal/nhạc nguồn: chạy thêm `install_demucs.bat`.

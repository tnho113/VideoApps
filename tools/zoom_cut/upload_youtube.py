"""Đăng video lên YouTube (mặc định chế độ RIÊNG TƯ để bạn xem lại trước).

Cần file client_secret.json (OAuth "Desktop app") từ Google Cloud Console, đã bật YouTube Data API v3.
Lần đầu chạy: mở link, đăng nhập, cho phép; trình duyệt sẽ chuyển tới trang lỗi "localhost" —
copy NGUYÊN địa chỉ trên thanh trình duyệt dán vào ô nhập. Token được lưu lại cho lần sau.

    python upload_youtube.py video.mp4 --title "..." --description "..." --thumbnail thumb.jpg \
        --client-secret client_secret.json --token youtube_token.json
"""
import argparse
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]


def get_credentials(client_secret, token_path):
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    if not creds or not creds.valid:
        os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"  # chỉ để nhận mã từ http://localhost
        flow = InstalledAppFlow.from_client_secrets_file(
            client_secret, SCOPES, redirect_uri="http://localhost:1")
        url, _ = flow.authorization_url(access_type="offline", prompt="consent")
        print("1) Mở link này và cho phép:\n", url)
        resp = input("2) Dán địa chỉ trang localhost sau khi cho phép: ").strip()
        flow.fetch_token(authorization_response=resp)
        creds = flow.credentials
    with open(token_path, "w") as f:
        f.write(creds.to_json())
    return creds


def upload(video, title, description, tags, thumbnail, privacy, creds, captions=None):
    yt = build("youtube", "v3", credentials=creds)
    body = {"snippet": {"title": title[:100], "description": description[:5000],
                        "tags": tags, "categoryId": "27"},  # 27 = Education
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    req = yt.videos().insert(part="snippet,status", body=body,
                             media_body=MediaFileUpload(video, chunksize=8 * 1024 * 1024,
                                                        resumable=True))
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
        if status:
            print(f"Đang tải lên… {int(status.progress() * 100)}%")
    vid = resp["id"]
    print(f"Đã đăng: https://youtu.be/{vid} ({privacy})")
    if thumbnail:
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(thumbnail)).execute()
            print("Đã gắn thumbnail.")
        except Exception as e:  # kênh chưa xác minh số điện thoại sẽ không cho đặt thumbnail
            print("Chưa gắn được thumbnail (kênh cần xác minh tại youtube.com/verify):", e)
    if captions:
        try:
            yt.captions().insert(part="snippet", body={"snippet": {
                "videoId": vid, "language": "vi", "name": "Phụ đề"}},
                media_body=MediaFileUpload(captions)).execute()
            print("Đã gắn phụ đề.")
        except Exception as e:
            print("Chưa gắn được phụ đề:", e)
    return vid


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", default="")
    ap.add_argument("--tags", default="", help="Cách nhau bằng dấu phẩy")
    ap.add_argument("--thumbnail")
    ap.add_argument("--captions", help="File .srt")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    ap.add_argument("--client-secret", default="client_secret.json")
    ap.add_argument("--token", default="youtube_token.json")
    a = ap.parse_args()
    creds = get_credentials(a.client_secret, a.token)
    tags = [t.strip() for t in a.tags.split(",") if t.strip()]
    upload(a.video, a.title, a.description, tags, a.thumbnail, a.privacy, creds, a.captions)


if __name__ == "__main__":
    main()

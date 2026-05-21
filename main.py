import cv2
import numpy as np
import qrcode
import base64


cap = cv2.VideoCapture(0)

detector = cv2.QRCodeDetector()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

MAX_SIZE = 300
MODE = "receive"
INPUT = "shrek.txt"
OUTPUT = "output"


def encode_frame(frame_type, seq=-1, data=""):
    return f"{frame_type}|{seq}|{data}"


def decode_frame(text):
    try:
        frame_type, seq, data = text.split("|", 2)
        return frame_type, int(seq), data
    except:
        return None, None, None


def chunk(data, size):
    i = 0
    seq = 0

    while i < len(data):
        yield seq, data[i : i + size]
        i += size
        seq += 1


def scan(target=None):
    while True:
        ret, frame = cap.read()
        if not ret:
            continue
        try:
            data, _, _ = detector.detectAndDecode(frame)
        except cv2.error:
            continue
        if data:
            print(data)
        if data and (data == target or not target):
            return data


def generate(data):
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color=0)
    img = np.array(img, dtype=np.uint8)

    img = cv2.resize(img, (1000, 1000), cv2.INTER_NEAREST)

    cv2.imshow("QR Generator", img)
    cv2.waitKey(1)


def sender(data):
    for seq, part in chunk(data, MAX_SIZE):
        generate(encode_frame("DATA", seq, part))
        scan(encode_frame("ACK", seq))

    generate(encode_frame("END"))


def receiver():
    data = ""
    seq = 0
    while True:
        frame_type, recived_seq, recived_data = decode_frame(scan())
        if frame_type == "END":
            return data
        if frame_type == "DATA" and recived_seq == seq:
            data += recived_data
            generate(encode_frame("ACK", seq))
            seq += 1


if MODE == "send":
    with open(INPUT, "rb") as f:
        data = base64.b64encode(f.read()).decode()

    sender(data)
elif MODE == "receive":
    data = receiver()

    with open(OUTPUT, "wb") as f:
        f.write(base64.b64decode(data.encode()))

cap.release()
cv2.destroyAllWindows()

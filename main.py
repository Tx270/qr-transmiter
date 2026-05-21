import cv2
import numpy as np
import qrcode
import base64

cap = cv2.VideoCapture(0)
detector = cv2.QRCodeDetector()

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

MAX_SIZE = 300
MODE = "send" 
INPUT = "shrek.txt"
OUTPUT = "output"


def encode_frame(frame_type, seq=0, data=""):
    return f"{frame_type}|{seq}|{data}"


def decode_frame(text):
    if not text:
        return None, None, None
    try:
        frame_type, seq, data = text.split("|", 2)
        return frame_type, int(seq), data
    except:
        return None, None, None


def chunk(data, size):
    seq = 1
    for i in range(0, len(data), size):
        yield seq, data[i:i + size]
        seq += 1


def read_frame():
    while True:
        ret, frame = cap.read()
        if cv2.waitKey(1) & 0xFF == ord('q'):
            return None
        if not ret:
            continue
        try:
            data, _, _ = detector.detectAndDecode(frame)
        except cv2.error:
            continue
        if data:
            return data


def wait_for_type(frame_type):
    while True:
        data = read_frame()
        t, seq, payload = decode_frame(data)
        if t == frame_type:
            return t, seq, payload


def wait_for_ack(seq):
    while True:
        t, rseq, _ = wait_for_type("ACK")
        if rseq == seq:
            return


def generate(data):
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color=0)
    img = np.array(img, dtype=np.uint8)
    img = cv2.resize(img, (600, 600), cv2.INTER_NEAREST)
    cv2.imshow("QR", img)
    cv2.waitKey(1)


def safe_b64decode(data):
    missing = len(data) % 4
    if missing:
        data += "=" * (4 - missing)
    return base64.b64decode(data.encode())


def sender(data, file_name):
    print("sending start...")
    generate(encode_frame("START", 0, file_name))
    wait_for_ack(0)
    
    print("sending data...")
    last_seq = 0
    for seq, part in chunk(data, MAX_SIZE):
        print(f"chunk {seq}")
        generate(encode_frame("DATA", seq, part))
        wait_for_ack(seq)
        last_seq = seq

    print("sending end...")
    generate(encode_frame("END", last_seq + 1, ""))
    wait_for_ack(last_seq + 1)
    print("done")


def receiver():
    buffer = ""
    print("waiting for start...")
    _, _, file_name = wait_for_type("START")
    print(f"file: {file_name}")
    generate(encode_frame("ACK", 0, ""))
    
    seq = 1
    temp_file = f"{OUTPUT}.tmp"

    while True:
        raw = read_frame()
        frame_type, received_seq, received_data = decode_frame(raw)

        if frame_type == "END":
            print("received end")
            generate(encode_frame("ACK", received_seq, ""))
            break

        if frame_type == "DATA":
            if received_seq == seq:
                print(f"chunk {received_seq}")
                buffer += received_data
                generate(encode_frame("ACK", received_seq, ""))
                seq += 1
            elif received_seq == seq - 1:
                generate(encode_frame("ACK", received_seq, ""))

    print("decoding...")
    try:
        with open(temp_file, "wb") as f:
            f.write(safe_b64decode(buffer))
    except Exception as e:
        print(f"error: {e}")

    return file_name, temp_file


try:
    if MODE == "send":
        with open(INPUT, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        sender(data, INPUT)

    elif MODE == "receive":
        file_name, temp_file = receiver()
        with open(file_name or OUTPUT, "wb") as out:
            with open(temp_file, "rb") as inp:
                out.write(inp.read())
        print(f"saved: {file_name}")

finally:
    cap.release()
    cv2.destroyAllWindows()
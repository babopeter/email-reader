import msg-extractor
import extract_msg
import os

def read_msg_file(file_path):
    if not os.path.exists(file_path):
        print("File not found:", file_path)
        return

    msg = extract_msg.Message(file_path)
    msg.extract()

    print("=== Email Information ===")
    print("Subject:", msg.subject)
    print("From:", msg.sender)
    print("To:", msg.to)
    print("CC:", msg.cc)
    print("Date:", msg.date)
    print("\n=== Email Body ===\n", msg.body)

    if msg.attachments:
        print("\n=== Attachments ===")
        for att in msg.attachments:
            print("Attachment:", att.longFilename or att.shortFilename)

if __name__ == "__main__":
    file_path = input("Enter the full path to your .msg file: ").strip()
    read_msg_file(file_path)
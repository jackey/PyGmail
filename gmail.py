# -*- coding: utf-8 -*-

import imaplib, email, base64
import os

attachmentpath = "./attachments";
if os.path.isdir(attachmentpath):
  os.mkdir(attachmentpath)

conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
conn.login("jziwenchen@gmail.com", "lovexx1314")

# 选择一个 inbox
conn.select("inbox")

# 执行search 命令

result, data = conn.uid("search", None, 'ALL')

ids = data[0]

id_list = ids.split()

result, email_data = conn.uid("fetch", id_list[-1], "(RFC822)")

gmail_mail = email.message_from_string(email_data[0][1])

# From
mfrom = email.utils.parseaddr(gmail_mail["From"])

# To: 
mto = email.utils.parseaddr(gmail_mail["To"])
headers = gmail_mail.items()

# Subject
subject = gmail_mail["subject"]


# Get attachment
for part in gmail_mail.walk():
  if part.get_content_maintype() == "multipart":
    continue
  if part.get("Content-Disposition") is None:
    continue
    
  filename = part.get_filename()
  
  if bool(filname):
    filepath = os.path.join(attachmentpath, filename)
    if not os.path.isfile(filepath):
      fp = open(filepath, "wb")
      fp.write(part.get_payload(decode=True))
      fp.close()
      
conn.close()
conn.logout()

    
  


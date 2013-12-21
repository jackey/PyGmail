import os.path
# -*- coding: utf-8 -*-


import imaplib, email, base64
from email.header import decode_header
import os
import sys
import subprocess
import pickle
import datetime
from ConfigParser import ConfigParser

basepath = os.path.abspath(os.path.dirname(__file__))

def is_media(file):
  """ 判断是否是Media (图片/视频) """
  cmd = "/usr/bin/file -b --mime-type %s" % (file)
  mime = subprocess.Popen(cmd, shell=True, \
  stdout = subprocess.PIPE).communicate()[0]
  mime = mime.rstrip()
  
  if mime in ["image/jpeg", "image/png", "image/jpg"]:
    return True
  return False

def cache_mail(uuid, gmail_mail, filepath):
  """缓存邮件内容"""
  print uuid
  # From
  mfrom = email.utils.parseaddr(gmail_mail["From"])
  # Subject
  subject = gmail_mail["Subject"]
  subject, encoding = decode_header(subject)[0]
  
  # 打印提示
  print "Cached %s Email with %s subject !" %(mfrom, subject)
  
  cache_dir = os.path.join(basepath, "caches")
  if not os.path.isdir(cache_dir):
    os.mkdir(cache_dir)
  
  cache_file = os.path.join(cache_dir, uuid);
  if os.path.isfile(cache_file):
    return False
  cache_data = [uuid, mfrom, subject, filepath]
  sdata = pickle.dumps(cache_data)
  fp = open(cache_file, "wb")
  fp.write(sdata)
  fp.close()
  
  
  return cache_data

def fetching_gamil(user, password):
  attachmentpath = "./attachments";
  attachmentpath = os.path.abspath(attachmentpath)
  if not os.path.isdir(attachmentpath):
    os.mkdir(attachmentpath)

  conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
  try:
    conn.login(user, password)
    conn.select("inbox")
  except:
    print "Error when login with %s" %(user)
    return

  # 选择一个 inbox

  # 执行search 命令
  # 只查询前2天的邮件 (多查询几天免得漏掉邮件)
  date = (datetime.date.today() - datetime.timedelta(2)).strftime("%d-%b-%Y")
  print "Fetching email since %s" %(date)
  result, data = conn.uid("search", None, "(SENTSINCE {date})".format(date=date))

  ids = data[0]
  id_list = ids.split()

  for eid in id_list:
    result, email_data = conn.uid("fetch", eid, "(RFC822)")

    gmail_mail = email.message_from_string(email_data[0][1])

    # Get attachment
    for part in gmail_mail.walk():
      if part.get_content_maintype() == "multipart":
        continue
      if part.get("Content-Disposition") is None:
        continue

      filename = "".join(part.get_filename().split())
      if bool(filename):
        filepath = os.path.join(attachmentpath, filename)
        if not os.path.isfile(filepath):
          fp = open(filepath, "wb")
          fp.write(part.get_payload(decode=True))
          fp.close()

        if is_media(filepath):
          data = cache_mail(eid, gmail_mail, filepath)
          if data:
            # 如果保存成功就发送数据到后台 保存
            pass

  conn.close()
  conn.logout()

if __name__ == "__main__":
  config = ConfigParser()
  config.read("count.ini")
  
  account = dict(config.items("section"))
  
  try:
    fetching_gamil(account['user'], account['pass'])
  except:
    print "Exception when fetch email !"

    
  


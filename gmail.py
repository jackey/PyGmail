# -*- coding: utf-8 -*-

import imaplib, email, base64
from email.header import decode_header
import os
import sys
import subprocess
import pickle
import datetime
from ConfigParser import ConfigParser
import os.path

basepath = os.path.abspath(os.path.dirname(__file__))

def post_media_to_bankwall(desc="description", user="xx@xx.com", media="/path/to/media"):
  sys.path.append(os.path.join(basepath, "poster"))
  from poster.encode import multipart_encode
  from poster.streaminghttp import register_openers
  import urllib2
  import json

  register_openers()
  
  datagen, headers = multipart_encode({"photo": open(os.path.join(basepath , media), "rb"), 
    "desc": desc,
    "user": user})
  request = urllib2.Request("http://bankwall.local/node/postbymail", datagen, headers)
  res = urllib2.urlopen(request).read()
  res = json.loads(res)
  return res["success"]

def reply_mail(mail_obj, is_success=True):
  print "begin to reply email to [%s] "  %(mail_obj["From"] or mail_obj["Reply-To"])
  original = mail_obj
  for part in original.walk():
    if (part.get("Content-Disposition")
      and part.get("Content-Disposition").startswith("attachment")):
        part.set_type("text/plain")
        part.set_payload("Attachment removed: %s (%s, %d bytes)"
                         %(part.get_filename(), 
                           part.get_content_type(), 
                           len(part.get_payload(decode=True))))
        del part["Content-Disposition"]
        del part["Content-Transfer-Encoding"]

  from email.mime.multipart import MIMEMultipart
  from email.mime.text import MIMEText
  from email.mime.message import MIMEMessage


  new = MIMEMultipart("mixed")
  body = MIMEMultipart("alternative")

  config = dict(load_config().items("reply"))
  body_reply = config['body'] if is_success else config["failed"]
  body.attach(MIMEText(body_reply, "plain"))
  body.attach(MIMEText("<p>"+ str(config["body"]) + "</p>", "html"))
  new.attach(body)

  new["Message-ID"] = email.utils.make_msgid()
  new["In-Reply-To"] = original["Message-ID"]
  new["References"] = original["Message-ID"]
  new["Subject"] = "Re: "+original["Subject"]
  new["To"] = original["Reply-To"] or original["From"]
  new["From"] = "jziwenchen@gmail.com"

  # new.attach(MIMEMessage(original))

  import smtplib
  mail_client = smtplib.SMTP("smtp.gmail.com", 587)
  mail_client.ehlo()
  mail_client.starttls()
  mail_client.ehlo()

  config = dict(load_config().items("smtp"))
  mail_client.login(config["user"], config["pass"])
  mail_client.sendmail(config["from"], [new["To"]], new.as_string())

  mail_client.quit()

  print "replied email to [%s] "  %(mail_obj["From"] or mail_obj["Reply-To"])
  

def is_media(file):
  """ 判断是否是Media (图片/视频) """
  cmd = "/usr/bin/file -b --mime-type %s" % (file)
  mime = subprocess.Popen(cmd, shell=True, \
  stdout = subprocess.PIPE).communicate()[0]
  mime = mime.rstrip()
  print "mime is [%s]" %(mime)
  
  if mime in ["image/jpeg", "image/png", "image/jpg", "image/gif"]:
    return True
  return False

def cache_mail(uuid, gmail_mail, filepath):
  """缓存邮件内容"""
  print "mail id [%s] is being to cached " %(uuid)
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

def is_cached(uuid):
  cache_dir = os.path.join(basepath, "caches")
  
  if not os.path.isdir(cache_dir):
    os.mkdir(cache_dir)
  
  cache_file = os.path.join(cache_dir, uuid)
  if not os.path.isfile(cache_file):
    return False
  return True

def fetching_gamil(user, password):
  # 只取最近10条邮件
  num = 10
  attachmentpath = "./attachments";
  attachmentpath = os.path.abspath(attachmentpath)
  if not os.path.isdir(attachmentpath):
    os.mkdir(attachmentpath)

  conn = imaplib.IMAP4_SSL("imap.gmail.com", 993)
  try:
    conn.login(user, password)
    print "login in mail account [%s] success" %(user)
    conn.select("inbox")
  except:
    print "Error when login with %s" %(user)
    return

  # 选择一个 inbox

  # 执行search 命令
  # 只查询前2天的邮件 (多查询几天免得漏掉邮件)
  date = (datetime.date.today() - datetime.timedelta(2)).strftime("%d-%b-%Y")
  print "Fetching email since %s" %("(SENTSINCE {date})".format(date=date))
  result, data = conn.uid("search", None, "(SENTSINCE {date})".format(date=date))
  # result, data = conn.uid("search", None, "ALL")

  ids = data[0]
  id_list = ids.split()

  print "ids [%s] of mail that be fetched " %(id_list)

  for eid in id_list:
    result, email_data = conn.uid("fetch", eid, "(RFC822)")

    gmail_mail = email.message_from_string(email_data[0][1])

    # Get attachment
    for part in gmail_mail.walk():
      if part.get_content_maintype() == "multipart":
        continue
      if part.get("Content-Disposition") is None:
        continue

      if part.get_filename() is None:
        continue
      filename = "".join(part.get_filename().split())

      # new file name
      import time
      nowtimestamp = int(time.time())
      filename = str(nowtimestamp) + filename

      if bool(filename):
        filepath = os.path.join(attachmentpath, filename)
        if not os.path.isfile(filepath):
          fp = open(filepath, "wb")
          fp.write(part.get_payload(decode=True))
          fp.close()
        else:
          # Exist same name file
          print "File : [%s] is downloaded" %(filepath)

        if is_media(filepath):
          # 在这里，先看是否已经有了缓存文件，如果有则不去发送图片到网站了
          if is_cached(eid):
            print "Mail with uuid [%s] is cached " %(eid)
            continue
          else:
          # 如果没有则先缓存图片再发送图片到网站
            data = cache_mail(eid, gmail_mail, filepath)

            if data is not None:
              print "begin to post data to bank wall"
              # 如果保存成功就发送数据到后台保存
              # From
              mfrom = email.utils.parseaddr(gmail_mail["From"])[1]
              # Subject
              subject = gmail_mail["Subject"]
              subject, encoding = decode_header(subject)[0]
              ret = post_media_to_bankwall(desc=subject, user=mfrom, media=filepath)
              reply_mail(gmail_mail, ret)
        else:
          print "File [%s] is not media " %(filepath)
  conn.close()
  conn.logout()

def load_config():
  try:
    config = ConfigParser()
    config.read("setting.ini")

    return config
  except Exception as e:
    print "setting.ini is not exists!"
    sys.exit(1)

if __name__ == "__main__":
  config = load_config()
  account = dict(config.items("mailaccount"))

  # There's only one process do fetch job in each time
  if not os.path.isfile(".lock"):
    f = open(".lock", "w+")
    f.close()
  
  f = open(".lock", "r+")
  p = f.read()
  print p
  # If empty, that means we can run it
  if len(p) == 0:
    f.write("True")
  # Otherwise, we exit it imedirecly
  else:
    print "Another process is runing"
    sys.exit(0)

  f.close()

  try:
    print "begin fetch mail from account [%s] " %(account['user'])
    fetching_gamil(account['user'], account['pass'])

    # After finished fetching mail, we empty .lock file
    with open(".lock", "w+") as f:
      f.write("")

  except Exception as e:
    print "Exception when fetch email !"
    os.unlink(".lock")
    print e

    
  


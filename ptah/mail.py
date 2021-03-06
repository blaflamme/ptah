""" mail settings """
import colander
from email.Utils import formataddr
from email import Encoders
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
from email.MIMENonMultipart import MIMENonMultipart
from email.Utils import formatdate, formataddr
from email.Header import make_header
from email.Charset import Charset

from ptah import config
from ptah.settings import MAIL


class MailGenerator(object):
    """ mail generator """

    def __init__(self, context):
        self._headers = {}
        self.context = context

    def _addHeader(self, header, value, encode=False):
        self._headers[header] = (header, value, encode)

    def setHeaders(self, message):
        charset = str(self.context.charset)

        extra = list(self.context.getHeaders())
        for key, val, encode in self._headers.values() + extra:
            if encode:
                message[key] = make_header(((val, charset),))
            else:
                message[key] = val

    def getMessage(self):
        """ render a mail template """
        context = self.context

        charset = str(context.charset)
        contentType = context.contentType

        mail_body = context.render()
        maintype, subtype = contentType.split('/')

        message = MIMEText(
            mail_body.encode(charset), subtype, charset)

        return message

    def getAttachments(self):
        attachments = []

        # attach files
        for data, content_type, filename, disposition in \
                self.context.getAttachments():
            maintype, subtype = content_type.split('/')

            msg = MIMENonMultipart(maintype, subtype)

            msg.set_payload(data)
            if filename:
                msg['Content-Id'] = '<%s@z3ext>' % filename
                msg['Content-Disposition'] = '%s; filename="%s"' % (
                    disposition, filename)

            Encoders.encode_base64(msg)

            attachments.append(msg)

        return attachments

    def message(self, multipart_format='mixed', *args, **kw):
        context = self.context

        # generate message
        message = self.getMessage()

        # generate attachments
        attachments = self.getAttachments()
        if attachments:
            # create multipart message
            root = MIMEMultipart(multipart_format)

            # insert headers
            self.setHeaders(root)

            # create message with attachments
            related = MIMEMultipart('related')
            related.attach(message)

            for attach in attachments:
                disposition = attach['Content-Disposition'].split(';')[0]
                if disposition == 'attachment':
                    root.attach(attach)
                else:
                    related.attach(attach)

            root.attach(related)
            message = root

        # alternative
        alternatives = self.context.getAlternative()
        if alternatives:
            mainmessage = MIMEMultipart('alternative')
            mainmessage.attach(message)

            for msg in alternatives:
                mainmessage.attach(MailGenerator(msg).message(
                        multipart_format, *args, **kw))

            message = mainmessage

        # default headers
        self._addHeader('Subject', context.subject, True)

        self.setHeaders(message)
        return message

    def __call__(self, multipart_format='mixed', *args, **kw):
        context = self.context
        message = self.message(multipart_format, *args, **kw)

        message['Date'] = formatdate()
        message['Message-ID'] = context.messageId

        #if not message.has_key('X-Mailer'):
        #    message['X-mailer'] = 'ptah.mailer'

        if not message.get('To') and context.to_address:
            message['To'] = context.to_address

        if not message.get('From') and context.from_address:
            message['From'] = formataddr(
                (context.from_name, context.from_address))

        return message


class MailTemplate(object):
    """ mail template with base features """

    subject = u''
    charset = u'utf-8'
    contentType = u'text/plain'
    messageId = None
    template = None

    from_name = ''
    from_address = ''
    to_address = ''
    return_address = ''
    errors_address = ''


    def __init__(self, context, request, **kwargs):
        self.__dict__.update(kwargs)

        self.context = context
        self.request = request

        self._files = []
        self._headers = {}
        self._alternative = []

    def addHeader(self, header, value, encode=False):
        self._headers[header] = (header, value, encode)

    def hasHeader(self, header):
        header = header.lower()
        for key in self._headers.keys():
            if key.lower() == header:
                return True

        return False

    def getHeaders(self):
        return self._headers.values()

    def addAttachment(self, file_data, content_type,
                      filename, disposition='attachment'):
        self._files.append((file_data, content_type,
                            wrap_filename(filename), disposition))

    def getAttachments(self):
        return self._files

    def addAlternative(self, template):
        self._alternative.append(template)

    def getAlternative(self):
        return self._alternative

    def update(self):
        self.from_name = MAIL.from_name
        self.from_address = MAIL.from_address

    def render(self):
        kwargs = {'view': self,
                  'context': self.context,
                  'request': self.request,
                  'nothing': None}

        return self.template(**kwargs)

    def send(self, emails=None, **kw):
        if emails:
            self.to_address = emails

        message = self(**kw)

        MAIL.Mailer.send(message['from'], message['to'], message)

    def __call__(self, **kw):
        for key, value in kw.items():
            if type(value) is tuple:
                self.addHeader(key, value[0], value[1])
            else:
                self.addHeader(key, value)

        self.update()
        return MailGenerator(self)()


def wrap_filename(f_name):
    dir, f_name = os.path.split(f_name)
    f_name = f_name.split('\\')[-1].split('/')[-1]
    for key in '~,\'':
        f_name = f_name.replace(key, '_')

    return f_name

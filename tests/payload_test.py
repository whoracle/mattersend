import re
import mattersend
from pyfakefs import fake_filesystem_unittest

try:
    from unittest import mock
except ImportError:
    import mock


def normalize_payload(payload):
    lines = []
    for line in payload.splitlines():
        lines.append(line.rstrip())
    return "\n".join(lines)


class MockResponse:
    def __init__(self, url, data):
        self.text = 'test'
        if url.endswith('/fail'):
            self.status_code = 502


class PayloadTest(fake_filesystem_unittest.TestCase):
    def setUp(self):
        self.setUpPyfakefs()
        self.fs.CreateFile('/etc/mattersend.conf', contents='''[DEFAULT]
url=https://chat.mydomain.com/hooks/abcdefghi123456

[angrybot]
icon = :angry:
username = AngryBot''')
        self.fs.CreateFile('/etc/mime.types', contents='text/x-diff diff')
        self.fs.CreateFile('/home/test/source.coffee', contents='x' * 5000)
        self.fs.CreateFile('/home/test/source.csv',
                           contents='abc,def\nfoo,bar')
        self.fs.CreateFile('/home/test/source.diff')
        self.fs.CreateFile('/home/test/Makefile')
        self.maxDiff = 20000

    def test_simple_1(self):
        payload = mattersend.send(channel='town-square',
                                  message='test message',
                                  just_return=True)

        self.assertEqual(normalize_payload(payload),
                         r"""POST https://chat.mydomain.com/hooks/abcdefghi123456
{
    "channel": "town-square",
    "text": "test message"
}""")

    def test_section(self):
        payload = mattersend.send(channel='town-square',
                                  message='test message',
                                  config_section='angrybot',
                                  just_return=True)

        self.assertEqual(normalize_payload(payload),
                         r"""POST https://chat.mydomain.com/hooks/abcdefghi123456
{
    "channel": "town-square",
    "icon_url": "https://chat.mydomain.com/static/emoji/1f620.png",
    "text": "test message",
    "username": "AngryBot"
}""")

    def test_override_url(self):
        payload = mattersend.send(channel='town-square',
                                  message='test message',
                                  url='http://chat.net/hooks/abdegh12',
                                  just_return=True)

        self.assertEqual(normalize_payload(payload),
                         r"""POST http://chat.net/hooks/abdegh12
{
    "channel": "town-square",
    "text": "test message"
}""")

    def test_syntax_by_ext(self):
        payload = mattersend.send(channel='town-square',
                                  filename='/home/test/source.coffee',
                                  just_return=True)

        content = r"```coffeescript\n%s```" % ('x' * 5000,)
        self.assertEqual(normalize_payload(payload),
                         r"""POST https://chat.mydomain.com/hooks/abcdefghi123456
{
    "attachments": [
        {
            "fallback": "%s",
            "text": "%s",
            "title": "source.coffee"
        }
    ],
    "channel": "town-square",
    "text": ""
}""" % (content[:3501], content[:3501]))

    def test_syntax_by_mime(self):
        payload = mattersend.send(channel='town-square',
                                  filename='/home/test/source.diff',
                                  just_return=True)

        self.assertEqual(normalize_payload(payload),
                         r"""POST https://chat.mydomain.com/hooks/abcdefghi123456
{
    "attachments": [
        {
            "fallback": "```diff\n```",
            "text": "```diff\n```",
            "title": "source.diff"
        }
    ],
    "channel": "town-square",
    "text": ""
}""")

    def test_syntax_mk(self):
        payload = mattersend.send(channel='town-square',
                                  filename='/home/test/Makefile',
                                  just_return=True)

        self.assertEqual(normalize_payload(payload),
                         r"""POST https://chat.mydomain.com/hooks/abcdefghi123456
{
    "attachments": [
        {
            "fallback": "```makefile\n```",
            "text": "```makefile\n```",
            "title": "Makefile"
        }
    ],
    "channel": "town-square",
    "text": ""
}""")

    def test_filename_and_message(self):
        payload = mattersend.send(channel='town-square',
                                  filename='/etc/mime.types',
                                  message='test message',
                                  just_return=True)

        self.assertEqual(normalize_payload(payload),
                         r"""POST https://chat.mydomain.com/hooks/abcdefghi123456
{
    "attachments": [
        {
            "fallback": "text/x-diff diff",
            "text": "text/x-diff diff",
            "title": "mime.types"
        }
    ],
    "channel": "town-square",
    "text": "test message"
}""")

    def test_fileinfo(self):
        payload = mattersend.send(channel='town-square',
                                  filename='/home/test/source.coffee',
                                  fileinfo=True,
                                  just_return=True)

        content = r"```coffeescript\n%s```" % ('x' * 5000,)
        self.assertEqual(normalize_payload(payload),
                         r"""POST https://chat.mydomain.com/hooks/abcdefghi123456
{
    "attachments": [
        {
            "fallback": "%s",
            "fields": [
                {
                    "short": true,
                    "title": "Size",
                    "value": "4.9KiB"
                },
                {
                    "short": true,
                    "title": "Mime",
                    "value": "None"
                }
            ],
            "text": "%s",
            "title": "source.coffee"
        }
    ],
    "channel": "town-square",
    "text": ""
}""" % (content[:3501], content[:3501]))

    def test_csv(self):
        payload = mattersend.send(channel='town-square',
                                  filename='/home/test/source.csv',
                                  tabular='sniff',
                                  just_return=True)

        self.assertEqual(normalize_payload(payload),
                         r"""POST https://chat.mydomain.com/hooks/abcdefghi123456
{
    "attachments": [
        {
            "fallback": "| abc | def |\n| --- | --- |\n| foo | bar |",
            "text": "| abc | def |\n| --- | --- |\n| foo | bar |",
            "title": "source.csv"
        }
    ],
    "channel": "town-square",
    "text": ""
}""")

    def test_csv_dialect(self):
        payload = mattersend.send(channel='town-square',
                                  filename='/home/test/source.csv',
                                  tabular='excel',
                                  just_return=True)

        self.assertEqual(normalize_payload(payload),
                         r"""POST https://chat.mydomain.com/hooks/abcdefghi123456
{
    "attachments": [
        {
            "fallback": "| abc | def |\n| --- | --- |\n| foo | bar |",
            "text": "| abc | def |\n| --- | --- |\n| foo | bar |",
            "title": "source.csv"
        }
    ],
    "channel": "town-square",
    "text": ""
}""")

    @mock.patch('requests.post', side_effect=MockResponse)
    def test_send(self, mock_post):
        payload = mattersend.send(channel='town-square',
                                  message='test message',
                                  url='http://chat.net/hooks/abdegh12')

    @mock.patch('requests.post', side_effect=MockResponse)
    def test_send(self, mock_post):
        with self.assertRaises(RuntimeError):
            payload = mattersend.send(channel='town-square',
                                      message='test message',
                                      url='http://chat.net/hooks/fail')

    def test_attachment(self):
        message = mattersend.Message()
        message.text = 'test_message'

        attachment = mattersend.Attachment('test_attachment')
        message.attachments.append(attachment)
        payload = message.get_payload()
        self.assertEqual(normalize_payload(payload), r"""{
    "attachments": [
        {
            "fallback": "test_attachment",
            "text": "test_attachment"
        }
    ],
    "text": "test_message"
}""")

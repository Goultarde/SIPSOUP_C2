import unittest
from unittest.mock import patch

from agent import execute
from sip import build, parse


class SipTest(unittest.TestCase):
    def test_agent_commands_are_allowlisted(self):
        self.assertEqual(execute("ping"), "pong")
        self.assertEqual(execute("bash -c id"), "commande refusée")

    @patch("sip.time.time", return_value=1000)
    def test_signed_round_trip_and_replay(self, _):
        seen = set()
        packet = build("MESSAGE", "agent-1", "c2", "ping", "secret")
        self.assertEqual(parse(packet, "secret", seen, 1000), ("MESSAGE", "agent-1", "c2", "ping"))
        with self.assertRaisesRegex(ValueError, "rejoue"):
            parse(packet, "secret", seen, 1000)

    @patch("sip.time.time", return_value=1000)
    def test_rejects_tampering(self, _):
        packet = build("MESSAGE", "agent-1", "c2", "ping", "secret").replace(b"ping", b"info")
        with self.assertRaisesRegex(ValueError, "signature"):
            parse(packet, "secret", set(), 1000)


if __name__ == "__main__":
    unittest.main()

import gzip
import io
import unittest
import zipfile

from appstoreconnect.api import Api, APIError


def _gzip(data):
	return gzip.compress(data)


def _zip(name, data):
	buf = io.BytesIO()
	with zipfile.ZipFile(buf, mode="w") as zf:
		zf.writestr(name, data)
	return buf.getvalue()


class UnwrapReportArchiveTest(unittest.TestCase):

	def test_plain_bytes_passthrough(self):
		payload = b"Date\tUnits\n2026-01-01\t5\n"
		self.assertEqual(Api._unwrap_report_archive(payload), payload)

	def test_bare_gzip(self):
		payload = b"report contents"
		self.assertEqual(Api._unwrap_report_archive(_gzip(payload)), payload)

	def test_zip_archive(self):
		payload = b"report contents"
		self.assertEqual(Api._unwrap_report_archive(_zip("report.txt", payload)), payload)

	def test_zip_with_gzipped_member(self):
		payload = b"report contents"
		archive = _zip("report.txt.gz", _gzip(payload))
		self.assertEqual(Api._unwrap_report_archive(archive), payload)

	def test_empty_zip_raises(self):
		buf = io.BytesIO()
		with zipfile.ZipFile(buf, mode="w"):
			pass
		with self.assertRaises(APIError):
			Api._unwrap_report_archive(buf.getvalue())

	def test_nesting_too_deep_raises(self):
		data = b"payload"
		for _ in range(6):  # exceeds default max_depth of 5
			data = _gzip(data)
		with self.assertRaises(APIError):
			Api._unwrap_report_archive(data)

	def test_real_subscription_report_zip_of_gzip(self):
		# App Store Connect subscription reports are tab-separated text shipped
		# as a zip archive whose single member is gzip-compressed. Mirror that
		# nesting and the actual decode path used by _api_call.
		tsv = (
			"Start Date\tEnd Date\tApp Name\tApp Apple ID\tSubscription Name\t"
			"Standard Subscription Duration\tCustomer Price\tActive Standard Price Subscriptions\n"
			"06/22/2026\t06/22/2026\tDino Rush\t123456789\tDino Rush Pro\t1 Month\t4.99\t1024\n"
		).encode("utf-8")
		archive = _zip("S_D_123456789_20260622.txt.gz", _gzip(tsv))

		report = Api._unwrap_report_archive(archive).decode("utf-8")

		self.assertEqual(report, tsv.decode("utf-8"))
		header = report.splitlines()[0].split("\t")
		self.assertIn("Active Standard Price Subscriptions", header)


if __name__ == "__main__":
	unittest.main()

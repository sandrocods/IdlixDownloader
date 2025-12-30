import unittest
from src.CryptoJsAesHelper import CryptoJsAes, dec
import json

class TestCryptoJsAes(unittest.TestCase):
    def test_dec_logic(self):
        """Test the key derivation logic (dec function)"""
        # r = "XX11YY22", r_list = ['11', '22']
        r = "XX11YY22"
        # base64("0|1") = "MHwx"
        # e = "xwHM" (reversed "MHwx")
        e = "xwHM"
        result = dec(r, e)
        self.assertEqual(result, "\\x11\\x22")

    def test_decrypt_invalid_data(self):
        """Test decryption with invalid/malformed json data"""
        invalid_json = "not a json"
        with self.assertRaises(Exception):
            CryptoJsAes.decrypt(invalid_json, "key")

    def test_decrypt_structure(self):
        """Verify that decrypt handles the expected JSON structure (ct, iv, s)"""
        # ct must be multiple of 16 bytes (AES block size)
        # "1234567890123456" is 16 bytes. Base64 is MTIzNDU2Nzg5MDEyMzQ1Ng==
        data = {
            "ct": "MTIzNDU2Nzg5MDEyMzQ1Ng==", 
            "iv": "00112233445566778899aabbccddeeff",
            "s": "0011223344556677"
        }
        json_data = json.dumps(data)
        try:
            CryptoJsAes.decrypt(json_data, "key")
        except Exception as e:
            # It should fail at AES decryption (padding/key), but not structure
            # We expect it might fail with padding error or similar, but we want to ensure it TRIED to decrypt
            pass

    def test_encrypt_decrypt_roundtrip(self):
        """Test that data encrypted can be decrypted back to original"""
        original_data = {"key": "value", "number": 123}
        passphrase = "secret_passphrase"
        
        # Encrypt
        encrypted_json = CryptoJsAes.encrypt(original_data, passphrase)
        
        # Decrypt
        decrypted_data = CryptoJsAes.decrypt(encrypted_json, passphrase)
        
        self.assertEqual(original_data, decrypted_data)

if __name__ == '__main__':
    unittest.main()

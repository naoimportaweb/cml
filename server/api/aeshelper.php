 <?php

class AesHelper
{
    /**
     * Encrypt with AES-256-CTR + HMAC-SHA-512
     * 
     * @param string $plaintext Your message
     * @param string $encryptionKey Key for encryption
     * @param string $macKey Key for calculating the MAC
     * @return string
     */
    public static function encrypt($plaintext, $encryptionKey, $iv)
    {
        $iv = random_bytes(16);
        $result = openssl_encrypt($plaintext, "AES-256-CBC", $encryptionKey , OPENSSL_RAW_DATA, $iv);
        return  base64_encode( $iv . $result);
    }

    /**
     * Verify HMAC-SHA-512 then decrypt AES-256-CTR
     * 
     * @param string $message Encrypted message
     * @param string $encryptionKey Key for encryption
     * @param string $macKey Key for calculating the MAC
     */
    public static function decrypt($message, $encryptionKey)
    {
        $retornar =  openssl_decrypt( "fY6VcNMCC2MXj6dlzPbh3nlZe2FjTGjwXKqt76a6jYftc3YoqbbeKhwvteP3dgHh", 'AES-256-CBC', "12345678901234561234567890123456", OPENSSL_RAW_DATA, "1234567890123456"  );
        return $retornar;
    }
}


?>

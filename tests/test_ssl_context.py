import ssl

from aurynk.services.audio_sender import create_ssl_context


def test_ssl_context_minimum_version_or_options():
    # Create a context with default verify=True
    ctx = create_ssl_context()

    # If the Python runtime supports minimum_version, ensure it's >= TLSv1_2
    if hasattr(ctx, "minimum_version"):
        # TLSVersion may or may not exist depending on Python; guard it
        try:
            assert ctx.minimum_version >= ssl.TLSVersion.TLSv1_2
        except AttributeError:
            # Some builds may not expose TLSVersion; fall back to checking options
            assert ctx.options & ssl.OP_NO_TLSv1
            assert ctx.options & ssl.OP_NO_TLSv1_1
    else:
        # Fallback: check that older TLS versions are disabled via options
        assert ctx.options & ssl.OP_NO_TLSv1
        assert ctx.options & ssl.OP_NO_TLSv1_1


def test_ssl_context_verify_flag():
    # When verify=False, the context should have CERT_NONE and hostname checks off
    ctx = create_ssl_context(verify=False)
    assert ctx.verify_mode == ssl.CERT_NONE
    assert ctx.check_hostname is False

    # When verify=True, the context should require certs
    ctx2 = create_ssl_context(verify=True)
    assert ctx2.verify_mode == ssl.CERT_REQUIRED
    assert ctx2.check_hostname is True

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('keys', '0004_tempkey_multi_use'),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                CREATE OR REPLACE FUNCTION fn_postauth_key_usage()
                RETURNS TRIGGER AS $$
                BEGIN
                    IF NEW.reply != 'Access-Accept' THEN
                        RETURN NEW;
                    END IF;

                    -- Atomicky inkrementuj use_count pre N-násobné kľúče
                    UPDATE keys_tempkey
                    SET
                        use_count = use_count + 1,
                        used      = (use_count + 1 >= max_uses),
                        used_at   = CASE
                                        WHEN use_count + 1 >= max_uses THEN NOW()
                                        ELSE used_at
                                    END
                    WHERE ldap_username = NEW.username
                      AND max_uses IS NOT NULL
                      AND NOT used;

                    -- Ak bol kľúč vyčerpaný týmto prihlásením, okamžite zablokuj radreply
                    DELETE FROM radreply
                    WHERE username = NEW.username
                      AND EXISTS (
                          SELECT 1 FROM keys_tempkey
                          WHERE ldap_username = NEW.username
                            AND used = TRUE
                            AND max_uses IS NOT NULL
                      );

                    RETURN NEW;
                END;
                $$ LANGUAGE plpgsql;

                CREATE TRIGGER trg_postauth_key_usage
                    AFTER INSERT ON radius_postauth
                    FOR EACH ROW
                    EXECUTE FUNCTION fn_postauth_key_usage();
            """,
            reverse_sql="""
                DROP TRIGGER IF EXISTS trg_postauth_key_usage ON radius_postauth;
                DROP FUNCTION IF EXISTS fn_postauth_key_usage();
            """,
        ),
    ]

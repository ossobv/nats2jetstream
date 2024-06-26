use crate::config_parser;


pub async fn connect(name: &str, server: &str, maybe_tls: &Option<config_parser::TlsConfig>, maybe_auth: &Option<config_parser::NatsAuth>)
-> Result<async_nats::Client, async_nats::ConnectError> {
    let mut options = async_nats::ConnectOptions::new()
        .name(name);

    if let Some(tls) = maybe_tls {
        options = options.require_tls(true);
        if tls.server_name.is_some() {
            eprintln!("warning: tls.server_name is not implemented");
        }
        if let Some(ca_file) = &tls.ca_file {
            options = options.add_root_certificates(ca_file.into());
        }
        if let (Some(cert), Some(key)) = (&tls.cert_file, &tls.key_file) {
            options = options.add_client_certificate(cert.into(), key.into());
        }
    }

    if let Some(auth) = maybe_auth {
        match (&auth.username, &auth.password) {
            (Some(username), Some(password)) => {
                options = options.user_and_password(username.to_owned(), password.to_owned());
            }
            _ => {
                eprintln!("warning: partial auth?");
            }
        }
    }

    options.connect(server).await
}

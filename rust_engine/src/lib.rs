use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use jni::objects::{JClass, JString};
use jni::sys::jint;
use jni::JNIEnv;
use lazy_static::lazy_static;
use std::net::UdpSocket;
use std::sync::{Arc, Mutex};

lazy_static! {
    static ref STREAM_HANDLE: Mutex<Option<cpal::Stream>> = Mutex::new(None);
    static ref IS_STREAMING: Mutex<bool> = Mutex::new(false);
}

#[no_mangle]
pub extern "system" fn Java_com_devindeed_aurelay_desktop_AudioEngine_startStream(
    mut env: JNIEnv,
    _class: JClass,
    target_ip: JString,
) -> jint {
    let target_ip: String = match env.get_string(&target_ip) {
        Ok(s) => s.into(),
        Err(_) => return -1,
    };

    let mut streaming = IS_STREAMING.lock().unwrap();
    if *streaming {
        return 0; // Already streaming
    }

    let host = cpal::default_host();

    // Find a suitable input device (monitor)
    let device = host.input_devices().ok().and_then(|mut devices| {
        devices.find(|d| {
            if let Ok(name) = d.name() {
                let name_lower = name.to_lowercase();
                // Prioritize monitor sources
                name_lower.contains("monitor") || name_lower.contains("analog stereo")
            } else {
                false
            }
        })
    }).or_else(|| host.default_input_device());

    let device = match device {
        Some(d) => d,
        None => return -2, // No device found
    };

    println!("AudioEngine: Using audio device: {}", device.name().unwrap_or("Unknown".to_string()));

    let config = match device.default_input_config() {
        Ok(c) => c,
        Err(_) => return -3,
    };

    let socket = match UdpSocket::bind("0.0.0.0:0") {
        Ok(s) => s,
        Err(_) => return -4,
    };

    // Target port 50051 (arbitrary, can be changed)
    let target = format!("{}:50051", target_ip);
    if socket.connect(&target).is_err() {
        return -5;
    }

    let socket = Arc::new(socket);
    let err_fn = |err| eprintln!("AudioEngine: an error occurred on stream: {}", err);

    let stream = match config.sample_format() {
        cpal::SampleFormat::F32 => {
            let socket = socket.clone();
            device.build_input_stream(
                &config.into(),
                move |data: &[f32], _: &_| {
                    // Convert f32 to bytes
                    let mut bytes = Vec::with_capacity(data.len() * 4);
                    for &sample in data {
                        bytes.extend_from_slice(&sample.to_le_bytes());
                    }
                    // Send UDP
                    let _ = socket.send(&bytes);
                },
                err_fn,
                None,
            )
        }
        cpal::SampleFormat::I16 => {
            let socket = socket.clone();
            device.build_input_stream(
                &config.into(),
                move |data: &[i16], _: &_| {
                    let mut bytes = Vec::with_capacity(data.len() * 2);
                    for &sample in data {
                        bytes.extend_from_slice(&sample.to_le_bytes());
                    }
                    let _ = socket.send(&bytes);
                },
                err_fn,
                None,
            )
        }
        cpal::SampleFormat::U16 => {
            let socket = socket.clone();
            device.build_input_stream(
                &config.into(),
                move |data: &[u16], _: &_| {
                    let mut bytes = Vec::with_capacity(data.len() * 2);
                    for &sample in data {
                        bytes.extend_from_slice(&sample.to_le_bytes());
                    }
                    let _ = socket.send(&bytes);
                },
                err_fn,
                None,
            )
        }
        _ => return -6, // Unsupported format
    };

    let stream = match stream {
        Ok(s) => s,
        Err(_) => return -7,
    };

    if stream.play().is_err() {
        return -8;
    }

    *STREAM_HANDLE.lock().unwrap() = Some(stream);
    *streaming = true;

    0
}

#[no_mangle]
pub extern "system" fn Java_com_devindeed_aurelay_desktop_AudioEngine_stopStream(
    _env: JNIEnv,
    _class: JClass,
) {
    let mut streaming = IS_STREAMING.lock().unwrap();
    if *streaming {
        let mut stream_handle = STREAM_HANDLE.lock().unwrap();
        *stream_handle = None;
        *streaming = false;
        println!("AudioEngine: Stream stopped");
    }
}

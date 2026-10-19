# MQTT GNSS/SDR Latency Testbed

Python 3.11 benchmark for measuring MQTT request-response round-trip time (RTT) over a Wi-Fi network. The testbed compares JSON, NMEA 0183, Protocol Buffers, MessagePack, and TOON for small GNSS records. For payload-size experiments, it transmits **synthetically generated** BladeRF-like SC16 Q11 IQ bytes using MessagePack.

## Experimental setup

- **Node 1 (MacBook Air, macOS):** Eclipse Mosquitto broker on TCP port 1883 and the Python publisher/benchmark.
- **Node 2 (Ubuntu Server):** Python subscriber (`run_server.py`) which decodes an incoming request and publishes an encoded response through the same broker. Ubuntu configurations: `generic` or `realtime` (PREEMPT_RT), tested in separate runs.
- **Network:** both machines connect to the same IEEE 802.11n Wi-Fi network. In the original setup, the broker on Node 1 was reached at `192.168.0.102:1883` from Node 2.

The publisher connects to its **local** broker (`localhost:1883`); `localhost` in the publisher log does **not** mean that the subscriber is running on the MacBook. The end-to-end RTT includes two-way network delivery and application-level processing; initial serialization of the outgoing request happens before RTT timing starts.

## Install

On **both** machines, from the repository directory:

```bash
python3.11 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

The `toon_format` dependency is pinned to a specific Git commit, so installation requires Git and network access. The Protobuf implementation can use `mqtt_gnss/proto/gnss_runtime.py`; **`grpcio-tools` and manual `.proto` compilation are not required** for this repository.

## Run the two-node experiment

**1. MacBook / Node 1:** Start the MQTT broker with a configuration that listens on the Wi-Fi interface (`listener 1883 0.0.0.0`). For an isolated, trusted lab network only, an unauthenticated listener may use `allow_anonymous true`. Do not expose such a listener to the public Internet; use authentication for other environments.

**2. Ubuntu / Node 2:** Start the subscriber (substitute the current IP address of the MacBook if it changed):

```bash
MQTT_HOST=192.168.0.102 python run_server.py
```

**3. MacBook / Node 1:** Perform a short smoke test of ten requests:

```bash
GNSS_ITERATIONS=10 MQTT_HOST=localhost python run_client.py --formats msgpack --chart ""
```

For the five-serializer comparison used in the project (1,000 and 10,000 requests per serializer):

```bash
MQTT_HOST=localhost python measure_mqtt.py --sizes 1000 10000 --formats json nmea protobuf msgpack toon
```

## MQTT payload-size benchmarks

Run these commands on Node 1 while the Node 2 subscriber is running:

```bash
# Baseline GNSS messages, no IQ payload: 1,000 iterations
python measure_mqtt.py --sizes 1000 --formats msgpack

# Synthetic 512 KiB IQ payload: 1,000 iterations
GNSS_TIMEOUT=30 python measure_mqtt.py --sizes 1000 --formats msgpack --payload-size 524288

# Synthetic 1 MiB IQ payload: 500 iterations
GNSS_TIMEOUT=30 python measure_mqtt.py --sizes 500 --formats msgpack --payload-size 1048576

# Synthetic 10 MiB IQ payload: 100 iterations
GNSS_TIMEOUT=60 python measure_mqtt.py --sizes 100 --formats msgpack --payload-size 10485760
```

Each command produces a CSV file with columns `Method`, `Time_s`, and `Time_ms`. The experiment uses MQTT QoS 0 by default, but still waits for a **matching application-level response**; requests that time out do not produce an RTT row. Different Ubuntu kernels must be selected separately on Node 2; the script does not switch kernels.

**Warning:** `measure_mqtt.py` overwrites output CSV files if names match existing files. Back up previous measurements before rerunning it. By default, running `python measure_mqtt.py` **without `--sizes`** executes 1,000, 10,000, **and 100,000** iterations per format; the 100,000-iteration option exists in the source but is not part of the paper's initial five-format comparison.

## Measurement notes

- The publisher measures RTT using `time.monotonic()` from just before publishing to receiving the matching response (`seq`). Outbound serialization occurs outside this interval.
- The subscriber deserializes and re-serializes a GNSS record before replying on `gnss/<format>/resp`.
- The configured warmup is 5 requests by default; warmup responses are not saved to CSV. Default QoS is 0, keepalive 30 seconds, and response timeout 5 seconds (override `GNSS_TIMEOUT` for larger payloads).
- The `msgpack` serializer supports the additional binary `payload` field in this codebase. Other included serializer implementations do not transmit that field; this is a limitation of these implementations, not of the formats themselves.
- A CSV contains successful RTT samples only; it does not record the number or causes of unsuccessful requests. Benchmark console logs provide per-format error counts.
- The synthetic IQ generator (`tools/bladerf_gen.py`) produces simulated SC16 Q11 samples and **does not read IQ samples from physical SDR hardware**.
- Experimental CSV datasets, credentials, and generated binary payloads are intentionally excluded by `.gitignore`.

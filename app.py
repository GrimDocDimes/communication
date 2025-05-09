import streamlit as st
import numpy as np
import plotly.graph_objects as go
from scipy import signal

# Set page config
st.set_page_config(
    page_title="Signal Modulation Oscilloscope",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .stPlotlyChart {
        background-color: #000000;
        border: 1px solid #333;
        border-radius: 5px;
    }
    .control-panel {
        background-color: #2b2b2b;
        padding: 0.5rem;
        border-radius: 5px;
        margin: 0.2rem 0;
    }
    .stSelectbox, .stSlider {
        margin-bottom: 0.5rem;
    }
    .channel-controls {
        border: 1px solid #444;
        padding: 0.5rem;
        margin: 0.5rem 0;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Signal generators
def generate_signal(signal_type, t, amplitude=1.0, frequency=1.0, offset=0.0):
    if signal_type == "Sine Wave":
        return amplitude * np.sin(2 * np.pi * frequency * t) + offset
    elif signal_type == "Square Wave":
        return amplitude * signal.square(2 * np.pi * frequency * t) + offset
    elif signal_type == "Triangle Wave":
        return amplitude * signal.sawtooth(2 * np.pi * frequency * t, 0.5) + offset
    elif signal_type == "Clock Pulse":
        return amplitude * signal.square(2 * np.pi * frequency * t, duty=0.5) + offset
    elif signal_type == "Binary Data":
        return amplitude * np.array([1 if np.random.random() > 0.5 else 0 for _ in range(len(t))]) + offset
    elif signal_type == "Carrier Wave":
        return amplitude * np.sin(2 * np.pi * frequency * t) + offset
    return np.zeros_like(t)

# Modulation

def modulate_signal(carrier_freq, message_signal, t, mod_type, mod_index=1.0):
    carrier = np.sin(2 * np.pi * carrier_freq * t)
    if mod_type == "AM":
        return (1 + mod_index * message_signal) * carrier
    elif mod_type == "FM":
        integrated_signal = np.cumsum(message_signal) * (t[1] - t[0])
        return np.sin(2 * np.pi * carrier_freq * t + mod_index * integrated_signal)
    elif mod_type == "PM":
        return np.sin(2 * np.pi * carrier_freq * t + mod_index * message_signal)
    elif mod_type == "ASK":
        return carrier * ((message_signal > 0) * 0.5 + 0.5)
    elif mod_type == "FSK":
        return np.where(message_signal > 0,
                        np.sin(2 * np.pi * carrier_freq * 1.5 * t),
                        np.sin(2 * np.pi * carrier_freq * t))
    elif mod_type == "PSK":
        return carrier * np.sign(message_signal)
    return np.zeros_like(t)

# Simple demodulation (envelope and threshold based)
def demodulate_signal(signal, mod_type):
    if mod_type == "AM":
        return np.abs(signal)
    elif mod_type == "FM" or mod_type == "PM":
        return np.gradient(np.unwrap(np.angle(signal + 1j*signal)))
    elif mod_type == "ASK":
        return signal > 0.1
    elif mod_type == "PSK" or mod_type == "FSK":
        return (signal > 0).astype(float)
    return np.zeros_like(signal)

# Plot

def plot_signals(t, signals, colors, names, visible):
    fig = go.Figure()
    for signal, color, name, is_visible in zip(signals, colors, names, visible):
        if is_visible:
            fig.add_trace(go.Scatter(x=t, y=signal, name=name, line=dict(color=color, width=2)))
    fig.update_layout(
        title="Signal Visualization",
        xaxis_title="Time (s)",
        yaxis_title="Amplitude (V)",
        height=600,
        plot_bgcolor='black',
        paper_bgcolor='black',
        font=dict(color='white'),
        margin=dict(l=20, r=20, t=40, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, bgcolor='rgba(0,0,0,0.5)'),
        xaxis=dict(gridcolor='#333', zerolinecolor='#666'),
        yaxis=dict(gridcolor='#333', zerolinecolor='#666', range=[-2, 2])
    )
    return fig

# Controls UI
def channel_controls(channel_num, key_prefix):
    with st.expander(f"Channel {channel_num} Controls", expanded=True):
        enabled = st.checkbox("Enable", value=True, key=f"{key_prefix}_enabled")
        tabs = st.tabs(["Modulation", "Demodulation"])
        with tabs[0]:
            mod_signal_options = [
                "Message Signal", "Clock Pulse", "Carrier Wave",
                "AM Modulated", "FM Modulated", "PM Modulated",
                "ASK Modulated", "PSK Modulated", "FSK Modulated"
            ]
            signal_type = st.selectbox("Select Modulation Signal", mod_signal_options, key=f"{key_prefix}_mod_signal")
        with tabs[1]:
            demod_signal_options = [
                "AM Demodulated", "FM Demodulated", "PM Demodulated",
                "ASK Demodulated", "PSK Demodulated", "FSK Demodulated"
            ]
            demod_selected = st.selectbox("Select Demodulation Signal", demod_signal_options, key=f"{key_prefix}_demod_signal")
        use_demod = st.radio("Use Signal From", ["Modulation", "Demodulation"], key=f"{key_prefix}_source")
        final_signal_type = demod_selected if use_demod == "Demodulation" else signal_type
        col1, col2 = st.columns(2)
        with col1:
            amplitude = st.slider("Amplitude (V)", 0.0, 2.0, 1.0, 0.1, key=f"{key_prefix}_amp")
            frequency = st.slider("Frequency (Hz)", 0.1, 10.0, 1.0, 0.1, key=f"{key_prefix}_freq")
        with col2:
            offset = st.slider("Offset (V)", -2.0, 2.0, 0.0, 0.1, key=f"{key_prefix}_offset")
            if "AM" in final_signal_type and "Modulated" in final_signal_type:
                mod_index = st.slider("Modulation Index", 0.0, 5.0, 1.0, 0.1, key=f"{key_prefix}_mod")
            else:
                mod_index = 1.0
        return enabled, final_signal_type, amplitude, frequency, offset, mod_index

# Main App

def main():
    st.title("3-Channel Signal Modulation Oscilloscope")
    t = np.linspace(0, 10, 10000)

    with st.sidebar:
        st.header("Global Settings")
        carrier_freq = st.slider("Carrier Frequency (Hz)", 1, 50, 10, key="global_carrier_freq")
        channels = []
        for i in range(3):
            st.markdown(f"<div class='channel-controls'>", unsafe_allow_html=True)
            channels.append(channel_controls(i+1, f"ch{i+1}"))
            st.markdown("</div>", unsafe_allow_html=True)

    signals, colors, names, visible = [], ['yellow', 'cyan', 'magenta'], [], []
    message_signal = generate_signal("Sine Wave", t, 1.0, 1.0, 0.0)
    carrier = generate_signal("Carrier Wave", t, 1.0, carrier_freq, 0.0)

    for i, (enabled, signal_type, amplitude, frequency, offset, mod_index) in enumerate(channels):
        if "Message Signal" in signal_type:
            signal = generate_signal("Sine Wave", t, amplitude, frequency, offset)
        elif "Clock Pulse" in signal_type:
            signal = generate_signal("Clock Pulse", t, amplitude, frequency, offset)
        elif "Carrier Wave" in signal_type:
            signal = generate_signal("Carrier Wave", t, amplitude, carrier_freq, offset)
        elif "Modulated" in signal_type:
            mod_type = signal_type.split()[0]
            signal = modulate_signal(carrier_freq, message_signal, t, mod_type, mod_index)
            signal = amplitude * signal + offset
        elif "Demodulated" in signal_type:
            mod_type = signal_type.split()[0]
            modulated = modulate_signal(carrier_freq, message_signal, t, mod_type, mod_index)
            signal = demodulate_signal(modulated, mod_type)
            signal = amplitude * signal + offset
        else:
            signal = np.zeros_like(t)

        signals.append(signal)
        names.append(f"CH{i+1}: {signal_type}")
        visible.append(enabled)

    col1, col2, col3 = st.columns([1, 10, 1])
    with col2:
        live_plot = st.empty()
        if 'frozen' not in st.session_state:
            st.session_state['frozen'] = False
        while not st.session_state['frozen']:
            fig = plot_signals(t, signals, colors, names, visible)
            live_plot.plotly_chart(fig, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Freeze", use_container_width=True):
            st.session_state['frozen'] = True
    with col2:
        if st.button("Run", use_container_width=True):
            st.session_state['frozen'] = False
    with col3:
        if st.button("Reset", use_container_width=True):
            st.experimental_rerun()

if __name__ == "__main__":
    main()

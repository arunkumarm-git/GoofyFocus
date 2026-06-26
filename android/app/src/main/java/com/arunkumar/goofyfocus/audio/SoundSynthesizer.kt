package com.arunkumar.goofyfocus.audio

import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioTrack
import java.util.Random
import kotlin.math.sin

object SoundSynthesizer {
    private var audioTrack: AudioTrack? = null
    private var playbackThread: Thread? = null
    @Volatile
    private var isPlaying = false
    private var currentType: String? = null

    fun play(type: String) {
        if (isPlaying && currentType == type) {
            return
        }
        stop()

        currentType = type
        isPlaying = true

        playbackThread = Thread {
            val sampleRate = 44100
            val channelConfig = AudioFormat.CHANNEL_OUT_STEREO
            val audioFormat = AudioFormat.ENCODING_PCM_16BIT
            val minBufferSize = AudioTrack.getMinBufferSize(sampleRate, channelConfig, audioFormat)
            val bufferSize = Math.max(minBufferSize, 44100)

            val track = try {
                AudioTrack(
                    AudioManager.STREAM_MUSIC,
                    sampleRate,
                    channelConfig,
                    audioFormat,
                    bufferSize,
                    AudioTrack.MODE_STREAM
                )
            } catch (e: Exception) {
                e.printStackTrace()
                isPlaying = false
                return@Thread
            }
            audioTrack = track

            try {
                track.play()
            } catch (e: Exception) {
                e.printStackTrace()
                isPlaying = false
                return@Thread
            }

            val random = Random()
            val shortBuffer = ShortArray(4096) // 2048 frames stereo
            
            // For binaural beats
            var phaseL = 0.0
            var phaseR = 0.0
            val carrierFreq = 200.0 // Hz
            val diffFreq = when (type) {
                "alpha" -> 10.0 // 10Hz Alpha Focus
                "theta" -> 6.0  // 6Hz Theta Deep Work
                else -> 0.0
            }
            val freqL = carrierFreq
            val freqR = carrierFreq + diffFreq

            val stepL = 2.0 * Math.PI * freqL / sampleRate
            val stepR = 2.0 * Math.PI * freqR / sampleRate

            // For brown noise filtering
            var lastOut = 0.0f

            while (isPlaying) {
                when (type) {
                    "white" -> {
                        for (i in 0 until shortBuffer.size step 2) {
                            val sample = (random.nextGaussian() * 0.15 * Short.MAX_VALUE).toInt()
                            val clamped = Math.max(Short.MIN_VALUE.toInt(), Math.min(Short.MAX_VALUE.toInt(), sample)).toShort()
                            shortBuffer[i] = clamped
                            shortBuffer[i + 1] = clamped
                        }
                    }
                    "brown" -> {
                        for (i in 0 until shortBuffer.size step 2) {
                            val white = (random.nextFloat() * 2f - 1f)
                            lastOut = (lastOut + (0.02f * white)) / 1.02f
                            val sample = (lastOut * 2.5f * Short.MAX_VALUE).toInt()
                            val clamped = Math.max(Short.MIN_VALUE.toInt(), Math.min(Short.MAX_VALUE.toInt(), sample)).toShort()
                            shortBuffer[i] = clamped
                            shortBuffer[i + 1] = clamped
                        }
                    }
                    "alpha", "theta" -> {
                        for (i in 0 until shortBuffer.size step 2) {
                            val valL = (sin(phaseL) * 0.3 * Short.MAX_VALUE).toInt()
                            val valR = (sin(phaseR) * 0.3 * Short.MAX_VALUE).toInt()

                            shortBuffer[i] = valL.toShort()
                            shortBuffer[i + 1] = valR.toShort()

                            phaseL += stepL
                            phaseR += stepR
                            
                            if (phaseL > 2.0 * Math.PI) phaseL -= 2.0 * Math.PI
                            if (phaseR > 2.0 * Math.PI) phaseR -= 2.0 * Math.PI
                        }
                    }
                }
                
                if (isPlaying) {
                    val written = track.write(shortBuffer, 0, shortBuffer.size)
                    if (written < 0) {
                        break
                    }
                }
            }

            try {
                track.stop()
                track.release()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
        playbackThread?.start()
    }

    fun stop() {
        isPlaying = false
        playbackThread?.interrupt()
        playbackThread = null
        currentType = null
        try {
            audioTrack?.stop()
            audioTrack?.release()
        } catch (e: Exception) {
            // Ignore
        }
        audioTrack = null
    }

    fun isPlaying(): Boolean = isPlaying
    
    fun getPlayingType(): String? = currentType

    fun playClickSound() {
        Thread {
            val sampleRate = 22050
            val numSamples = (0.05 * sampleRate).toInt() // 50ms
            val sample = DoubleArray(numSamples)
            val generatedSnd = ShortArray(numSamples)
            val freqOfTone = 800.0 // Hz
            
            for (i in 0 until numSamples) {
                val t = i.toDouble() / sampleRate
                val envelope = Math.exp(-t * 60.0) // fast decay
                sample[i] = sin(2.0 * Math.PI * freqOfTone * t) * envelope
                generatedSnd[i] = (sample[i] * Short.MAX_VALUE).toInt().toShort()
            }
            
            try {
                val track = AudioTrack(
                    AudioManager.STREAM_MUSIC,
                    sampleRate,
                    AudioFormat.CHANNEL_OUT_MONO,
                    AudioFormat.ENCODING_PCM_16BIT,
                    numSamples * 2,
                    AudioTrack.MODE_STATIC
                )
                track.write(generatedSnd, 0, numSamples)
                track.play()
                Thread.sleep(60)
                track.stop()
                track.release()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }.start()
    }

    fun playSuccessSound() {
        Thread {
            val sampleRate = 22050
            val duration1 = 0.08
            val duration2 = 0.15
            val samples1 = (duration1 * sampleRate).toInt()
            val samples2 = (duration2 * sampleRate).toInt()
            val totalSamples = samples1 + samples2
            val generatedSnd = ShortArray(totalSamples)
            
            for (i in 0 until samples1) {
                val t = i.toDouble() / sampleRate
                val envelope = if (i > samples1 - 200) (samples1 - i).toDouble() / 200.0 else 1.0
                generatedSnd[i] = (sin(2.0 * Math.PI * 523.25 * t) * 0.4 * Short.MAX_VALUE * envelope).toInt().toShort()
            }
            
            for (i in 0 until samples2) {
                val t = i.toDouble() / sampleRate
                val envelope = Math.exp(-t * 10.0) // nice smooth decay
                generatedSnd[samples1 + i] = (sin(2.0 * Math.PI * 659.25 * t) * 0.4 * Short.MAX_VALUE * envelope).toInt().toShort()
            }
            
            try {
                val track = AudioTrack(
                    AudioManager.STREAM_MUSIC,
                    sampleRate,
                    AudioFormat.CHANNEL_OUT_MONO,
                    AudioFormat.ENCODING_PCM_16BIT,
                    totalSamples * 2,
                    AudioTrack.MODE_STATIC
                )
                track.write(generatedSnd, 0, totalSamples)
                track.play()
                Thread.sleep(300)
                track.stop()
                track.release()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }.start()
    }
}

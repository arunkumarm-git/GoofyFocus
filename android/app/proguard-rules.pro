# Proguard rules for GoofyFocus Android app

# Keep Compose compiler annotations
-keepclassmembers class * {
    @androidx.compose.runtime.Composable *;
}

# Keep kotlinx serialization classes if used
-keepattributes *Annotation*,Signature,InnerClasses,EnclosingMethod

-keepclassmembers class * {
    *** Companion;
}

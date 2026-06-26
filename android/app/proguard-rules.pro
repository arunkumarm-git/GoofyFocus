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

# WorkManager ProGuard Rules
-keep class androidx.work.** { *; }

-keepclassmembers class * extends androidx.work.ListenableWorker {
    public <init>(android.content.Context, androidx.work.WorkerParameters);
}

# Room Database ProGuard Rules
-keep class * extends androidx.room.RoomDatabase {
    <init>(...);
}
-keep class * implements androidx.room.RoomOpenHelper

# Firebase ProGuard Rules
-keep class com.google.firebase.** { *; }
-dontwarn com.google.firebase.**

# Google Play Services ProGuard Rules
-keep class com.google.android.gms.** { *; }
-dontwarn com.google.android.gms.**



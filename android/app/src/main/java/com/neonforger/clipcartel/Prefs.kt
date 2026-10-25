package com.neonforger.clipcartel

import android.content.Context
import android.content.SharedPreferences

object Prefs {
    fun get(ctx: Context): SharedPreferences = ctx.getSharedPreferences("clipcartel", Context.MODE_PRIVATE)
}

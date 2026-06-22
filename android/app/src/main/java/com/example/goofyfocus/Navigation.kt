package com.example.goofyfocus

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.navigation3.runtime.entryProvider
import androidx.navigation3.runtime.rememberNavBackStack
import androidx.navigation3.ui.NavDisplay
import com.example.goofyfocus.ui.BreakOverlayScreen
import com.example.goofyfocus.ui.SettingsScreen
import com.example.goofyfocus.ui.main.MainScreen

@Composable
fun MainNavigation() {
  val backStack = rememberNavBackStack(Main)

  // Auto-navigate to BreakOverlay when triggered via MainActivity intent
  LaunchedEffect(Unit) {
    MainActivity.breakTrigger.collect { trigger ->
      if (trigger) {
        // Only navigate if we aren't already on the BreakOverlay screen
        if (backStack.none { it is BreakOverlay }) {
          backStack.add(BreakOverlay)
        }
      }
    }
  }

  NavDisplay(
    backStack = backStack,
    onBack = { backStack.removeLastOrNull() },
    entryProvider =
      entryProvider {
        entry<Main> {
          MainScreen(
            onItemClick = { navKey -> backStack.add(navKey) },
            modifier = Modifier.fillMaxSize()
          )
        }
        entry<Settings> {
          SettingsScreen(
            onBack = { backStack.removeLastOrNull() },
            modifier = Modifier.fillMaxSize()
          )
        }
        entry<BreakOverlay> {
          BreakOverlayScreen(
            onDismiss = { backStack.removeLastOrNull() },
            modifier = Modifier.fillMaxSize()
          )
        }
      },
  )
}

import { ActivityIndicator, StyleSheet, View } from "react-native";
import { StatusBar } from "expo-status-bar";
import {
  SpaceGrotesk_400Regular,
  SpaceGrotesk_500Medium,
  SpaceGrotesk_600SemiBold,
  SpaceGrotesk_700Bold,
  useFonts,
} from "@expo-google-fonts/space-grotesk";
import { TradingApp } from "./src/TradingApp";

export default function App() {
  const [fontsLoaded] = useFonts({
    Inter_400Regular: SpaceGrotesk_400Regular,
    Inter_500Medium: SpaceGrotesk_500Medium,
    Inter_600SemiBold: SpaceGrotesk_600SemiBold,
    Inter_700Bold: SpaceGrotesk_700Bold,
    Inter_800ExtraBold: SpaceGrotesk_700Bold,
  });

  if (!fontsLoaded) {
    return (
      <View style={styles.loader}>
        <StatusBar style="dark" />
        <ActivityIndicator size="large" color="#20A86F" />
      </View>
    );
  }

  return <TradingApp />;
}

const styles = StyleSheet.create({
  loader: {
    flex: 1,
    backgroundColor: "#F6FAF7",
    justifyContent: "center",
    alignItems: "center",
  },
});

package com.fongmi.android.tv;

import android.app.ActivityManager;
import android.content.Context;
import android.os.Process;
import android.util.Log;

import java.lang.reflect.Method;
import java.util.List;

/**
 * TMXK first-run bootstrap. The original App class remains the superclass.
 * This class is added as a new DEX; the official player DEX files stay intact.
 */
public final class New extends App {
    private static final String TAG = "TMXKBootstrap";
    private static final String VOD_URL = "http://www.饭太硬.cc/tv";
    private static final String LIVE_URL = "assets://tmxk/config.json";
    private static final String GAME_URL = "assets://tmxk/game-live-vod.json";

    @Override
    public void onCreate() {
        super.onCreate();
        if (!isMainProcess()) return;

        try {
            Class<?> config = Class.forName("com.fongmi.android.tv.bean.Config");
            Method getAll = config.getMethod("getAll", int.class);
            Method getUrl = config.getMethod("getUrl");
            Method create = config.getMethod("create", int.class, String.class, String.class);
            Method update = config.getMethod("update");

            register(getAll, getUrl, create, update, 0, VOD_URL, "饭太硬", true);
            register(getAll, getUrl, create, update, 1, LIVE_URL, "TMXK 内置直播", true);
            register(getAll, getUrl, create, update, 0, GAME_URL, "TMXK 游戏直播", false);
            Log.i(TAG, "Built-in VOD and live sources checked");
        } catch (Throwable error) {
            Log.e(TAG, "Unable to register built-in sources", error);
        }
    }

    private static void register(
            Method getAll, Method getUrl, Method create, Method update,
            int type, String url, String name, boolean selectWhenNew
    ) throws Exception {
        @SuppressWarnings("unchecked")
        List<Object> rows = (List<Object>) getAll.invoke(null, type);
        boolean wasEmpty = rows == null || rows.isEmpty();

        if (rows != null) {
            for (Object row : rows) {
                Object existingUrl = getUrl.invoke(row);
                if (url.equals(existingUrl)) return;
            }
        }

        Object config = create.invoke(null, type, url, name);
        if (selectWhenNew && wasEmpty) update.invoke(config);
    }

    private boolean isMainProcess() {
        String packageName = getPackageName();
        ActivityManager manager = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        List<ActivityManager.RunningAppProcessInfo> processes =
                manager == null ? null : manager.getRunningAppProcesses();
        if (processes != null) {
            for (ActivityManager.RunningAppProcessInfo process : processes) {
                if (process.pid == Process.myPid()) {
                    return packageName.equals(process.processName);
                }
            }
        }
        return false;
    }
}

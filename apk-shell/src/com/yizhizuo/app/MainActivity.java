package com.yizhizuo.app;

import android.app.Activity;
import android.content.ContentValues;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStream;

public class MainActivity extends Activity {

    private static final int BG = 0xFFF7F7F8;
    private static final String HOME_URL =
        "file:///android_asset/index.html";
    private static final int FILE_CHOOSER_REQUEST = 1001;

    private WebView web;
    private ValueCallback<Uri[]> uploadCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        applyChrome();

        web = new WebView(this);
        web.setBackgroundColor(BG);

        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setLoadWithOverviewMode(true);
        s.setUseWideViewPort(true);
        s.setBuiltInZoomControls(false);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);

        web.setWebViewClient(new WebViewClient() {            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme() == null ? "" : uri.getScheme().toLowerCase();
                if (scheme.equals("mailto") || scheme.equals("tel")
                        || scheme.equals("http") || scheme.equals("https")) {
                    try {
                        startActivity(new Intent(Intent.ACTION_VIEW, uri));
                        return true;
                    } catch (Exception e) {
                        return false;
                    }
                }
                return false;
            }
        });

        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView view, ValueCallback<Uri[]> callback,
                    FileChooserParams params) {
                if (uploadCallback != null) {
                    uploadCallback.onReceiveValue(null);
                }
                uploadCallback = callback;
                Intent intent = new Intent(Intent.ACTION_GET_CONTENT);
                intent.addCategory(Intent.CATEGORY_OPENABLE);
                intent.setType("*/*");
                try {
                    startActivityForResult(Intent.createChooser(intent, "Import"), FILE_CHOOSER_REQUEST);
                } catch (Exception e) {
                    uploadCallback.onReceiveValue(null);
                    uploadCallback = null;
                }
                return true;
            }
        });

        web.addJavascriptInterface(new SaveBridge(this), "PEW");

        setContentView(web);
        web.loadUrl(HOME_URL);
    }

    /**
     * 供页面导出备份使用：把文本写进系统「下载」目录，返回保存位置描述（失败返回空串）。
     * WebView 不触发 <a download>，因此在壳内必须由原生落盘。
     */
    private static class SaveBridge {
        private final Activity act;

        SaveBridge(Activity activity) {
            this.act = activity;
        }

        @JavascriptInterface
        public String saveText(String name, String text) {
            try {
                byte[] bytes = text.getBytes("UTF-8");
                if (Build.VERSION.SDK_INT >= 29) {
                    ContentValues v = new ContentValues();
                    v.put(MediaStore.MediaColumns.DISPLAY_NAME, name);
                    v.put(MediaStore.MediaColumns.MIME_TYPE, "application/json");
                    v.put(MediaStore.MediaColumns.RELATIVE_PATH, Environment.DIRECTORY_DOWNLOADS);
                    Uri uri = act.getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
                    if (uri == null) return "";
                    OutputStream os = act.getContentResolver().openOutputStream(uri);
                    if (os == null) return "";
                    os.write(bytes);
                    os.flush();
                    os.close();
                    return "Download/" + name;
                }
                File dir = act.getExternalFilesDir(Environment.DIRECTORY_DOWNLOADS);
                if (dir == null) dir = act.getFilesDir();
                if (!dir.exists() && !dir.mkdirs()) return "";
                File f = new File(dir, name);
                FileOutputStream fos = new FileOutputStream(f);
                fos.write(bytes);
                fos.flush();
                fos.close();
                return f.getAbsolutePath();
            } catch (Exception e) {
                return "";
            }
        }
    }

    private void applyChrome() {
        getWindow().setBackgroundDrawable(new ColorDrawable(BG));
        getWindow().setStatusBarColor(BG);
        getWindow().setNavigationBarColor(BG);

        int flags = 0;
        if (Build.VERSION.SDK_INT >= 23) {
            flags |= View.SYSTEM_UI_FLAG_LIGHT_STATUS_BAR;
        }
        if (Build.VERSION.SDK_INT >= 26) {
            flags |= View.SYSTEM_UI_FLAG_LIGHT_NAVIGATION_BAR;
        }
        if (flags != 0) {
            getWindow().getDecorView().setSystemUiVisibility(flags);
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == FILE_CHOOSER_REQUEST) {
            Uri[] results = null;
            if (uploadCallback != null) {
                if (resultCode == RESULT_OK && data != null && data.getData() != null) {
                    results = new Uri[]{data.getData()};
                }
                uploadCallback.onReceiveValue(results);
                uploadCallback = null;
            }
        }
    }

    @Override
    public void onBackPressed() {
        if (web != null && web.canGoBack()) {
            web.goBack();
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onDestroy() {
        if (web != null) {
            web.destroy();
            web = null;
        }
        super.onDestroy();
    }
}

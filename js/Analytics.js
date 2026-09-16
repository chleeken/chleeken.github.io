/**
 * 网站统计分析代码
 * 支持：代码统计 / 文字链接统计 / 图片链接统计/js代码统计
 */

(function() {
    'use strict';
    
    /**
     * 统计配置
     * 自定义 JS 脚本（异步加载）
     */
    var analyticsConfig = {
        // 自定义 JS 脚本（异步加载）
        scripts: [
            'js/tj.js'
        ],
        // 自定义统计
        custom: {
            enable: true,
            // 文字链接统计
            textLinks: [
                { text: '统计', href: '' }
            ],
            // 图片链接统计
            imageLinks: [
                { src: '', href: '', alt: '' }
            ]
        }
    };
    
    /**
     * 加载统计脚本
     */
    function loadAnalytics() {
        // 自定义 JS 脚本
        if (analyticsConfig.scripts && analyticsConfig.scripts.length > 0) {
            analyticsConfig.scripts.forEach(function(url) {
                var s = document.createElement('script');
                s.async = true;
                s.src = url;
                document.head.appendChild(s);
            });
        }
    }
    
    /**
     * 渲染统计信息到页脚
     */
    function renderAnalytics() {
        var footer = document.querySelector('.site-footer');
        if (!footer || !analyticsConfig.custom.enable) return;
        
        var statsHtml = '<div class="analytics-stats">';
        
        // 文字链接统计
        if (analyticsConfig.custom.textLinks && analyticsConfig.custom.textLinks.length > 0) {
            analyticsConfig.custom.textLinks.forEach(function(link) {
                statsHtml += '<a href="' + link.href + '" title="' + link.text + '">' + link.text + '</a> ';
            });
        }
        
        // 图片链接统计
        if (analyticsConfig.custom.imageLinks && analyticsConfig.custom.imageLinks.length > 0) {
            analyticsConfig.custom.imageLinks.forEach(function(img) {
                if (!img.src) return;
                statsHtml += '<a href="' + (img.href || '#') + '" title="' + (img.alt || '') + '"><img src="' + img.src + '" alt="' + (img.alt || '') + '" style="vertical-align:middle;margin:0 5px;"></a> ';
            });
        }
        
        statsHtml += '</div>';
        
        footer.insertAdjacentHTML('beforeend', statsHtml);
    }
    
    /**
     * 初始化
     */
    function init() {
        loadAnalytics();
        
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', renderAnalytics);
        } else {
            renderAnalytics();
        }
    }
    
    init();
})();










'use client';

import { useState, useEffect } from 'react';
import { X, Save, Loader2, Zap, Globe, Languages, Clock, DollarSign, CreditCard, CheckCircle2, AlertTriangle, Shield, User, Mail, Send, Wifi, Lock, Eye, EyeOff } from 'lucide-react';
import { UserProfile } from '@/types';
import { api, emailApi } from '@/lib/api';
import { cn } from '@/lib/utils';

interface SettingsPanelProps {
  onClose: () => void;
  onSave: () => void;
  onTestEmail: () => Promise<void>;
}

const experienceLevels = ['Beginner', 'Beginner/Intermediate', 'Intermediate', 'Advanced', 'Expert'];
const currencies = ['USD', 'EUR', 'GBP', 'EGP', 'SAR', 'AED'];
const jobTypes = ['fixed_price', 'hourly'];

interface EmailConfig {
  enabled: boolean;
  smtp_host: string;
  smtp_port: number;
  username: string;
  password: string;
  from_email: string;
  use_tls: boolean;
}

interface NotificationSettings {
  enabled: boolean;
  email: string;
  on_scan_complete: boolean;
  on_high_match: boolean;
  on_new_job: boolean;
}

export function SettingsPanel({ onClose, onSave, onTestEmail }: SettingsPanelProps) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [emailConfig, setEmailConfig] = useState<EmailConfig>({
    enabled: true,
    smtp_host: 'smtp.gmail.com',
    smtp_port: 587,
    username: '',
    password: '',
    from_email: '',
    use_tls: true
  });
  const [notifications, setNotifications] = useState<NotificationSettings>({
    enabled: true,
    email: 'islam230366qw@gmail.com',
    on_scan_complete: true,
    on_high_match: true,
    on_new_job: false
  });
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'profile' | 'skills' | 'preferences' | 'email'>('profile');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [testingEmail, setTestingEmail] = useState(false);

  useEffect(() => {
    loadProfile();
    loadEmailSettings();
  }, []);

  const loadProfile = async () => {
    try {
      const res = await api.get('/api/config');
      setProfile(res.data.profile);
      if (res.data.email_config) {
        setEmailConfig(prev => ({ ...prev, ...res.data.email_config }));
      }
      if (res.data.email_notifications) {
        setNotifications(res.data.email_notifications);
      }
    } catch (error) {
      console.error('Failed to load profile:', error);
    }
  };

  const loadEmailSettings = async () => {
    try {
      const res = await emailApi.getSettings();
      if (res.data.email_config) {
        setEmailConfig(prev => ({ ...prev, ...res.data.email_config }));
      }
      if (res.data.notifications) {
        setNotifications(res.data.notifications);
      }
    } catch (error) {
      console.error('Failed to load email settings:', error);
    }
  };

  const handleSave = async () => {
    if (!profile) return;
    setSaving(true);
    setMessage(null);
    try {
      await api.post('/api/config/profile', profile);
      await emailApi.updateSettings({
        enabled: emailConfig.enabled,
        smtp_host: emailConfig.smtp_host,
        smtp_port: emailConfig.smtp_port,
        username: emailConfig.username,
        password: emailConfig.password,
        from_email: emailConfig.from_email,
        use_tls: emailConfig.use_tls
      });
      await emailApi.updateNotifications({
        enabled: notifications.enabled,
        email: notifications.email,
        on_scan_complete: notifications.on_scan_complete,
        on_high_match: notifications.on_high_match,
        on_new_job: notifications.on_new_job
      });
      setMessage({ type: 'success', text: 'تم حفظ جميع الإعدادات بنجاح' });
      onSave();
    } catch (error) {
      setMessage({ type: 'error', text: 'فشل الحفظ، حاول مرة أخرى' });
    } finally {
      setSaving(false);
    }
  };

  const handleChange = <K extends keyof UserProfile>(key: K, value: UserProfile[K]) => {
    setProfile(prev => prev ? { ...prev, [key]: value } : null);
  };

  const handleEmailConfigChange = <K extends keyof EmailConfig>(key: K, value: EmailConfig[K]) => {
    setEmailConfig(prev => ({ ...prev, [key]: value }));
  };

  const handleNotificationChange = <K extends keyof NotificationSettings>(key: K, value: NotificationSettings[K]) => {
    setNotifications(prev => ({ ...prev, [key]: value }));
  };

  const addSkill = (skill: string) => {
    if (!profile || !skill.trim()) return;
    const newSkills = [...new Set([...profile.skills, skill.trim()])];
    handleChange('skills', newSkills);
  };

  const removeSkill = (skill: string) => {
    if (!profile) return;
    handleChange('skills', profile.skills.filter(s => s !== skill));
  };

  const handleTestEmail = async () => {
    setTestingEmail(true);
    try {
      await onTestEmail();
    } finally {
      setTestingEmail(false);
    }
  };

  if (!profile) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <div className="bg-white rounded-xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-100 sticky top-0 bg-white">
          <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Zap className="h-5 w-5 text-yellow-500" />
            الإعدادات والملف الشخصي
          </h2>
          <button onClick={onClose} className="p-2 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="border-b border-gray-100 bg-gray-50 px-4">
          <nav className="flex gap-1" aria-label="Settings tabs">
            {[
              { id: 'profile', label: 'الملف الشخصي', icon: <User className="h-4 w-4" /> },
              { id: 'skills', label: 'المهارات', icon: <Zap className="h-4 w-4" /> },
              { id: 'preferences', label: 'التفضيلات', icon: <Globe className="h-4 w-4" /> },
              { id: 'email', label: 'البريد والإشعارات', icon: <Mail className="h-4 w-4" /> },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={cn(
                  'flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors',
                  activeTab === tab.id
                    ? 'text-primary-600 border-primary-600 bg-white'
                    : 'text-gray-500 hover:text-gray-700 hover:bg-gray-100'
                )}
              >
                {tab.icon} {tab.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-6">
          {message && (
            <div className={cn(
              'p-3 rounded-lg text-sm flex items-center gap-2',
              message.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
            )}>
              {message.type === 'success' ? <CheckCircle2 className="h-4 w-4" /> : <AlertTriangle className="h-4 w-4" />}
              {message.text}
            </div>
          )}

          {/* Profile Tab */}
          {activeTab === 'profile' && (
            <div className="space-y-6">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <User className="h-5 w-5" /> المعلومات الشخصية
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">الاسم الكامل</label>
                  <input
                    type="text"
                    value={profile.bio.split('\n')[0] || ''}
                    onChange={(e) => handleChange('bio', e.target.value + '\n' + (profile.bio.split('\n').slice(1).join('\n') || ''))}
                    className="input"
                    placeholder="اسمك"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">الموقع</label>
                  <input
                    type="text"
                    value={profile.location}
                    onChange={(e) => handleChange('location', e.target.value)}
                    className="input"
                    placeholder="مثال: مصر، القاهرة"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">التوفر</label>
                  <select
                    value={profile.availability}
                    onChange={(e) => handleChange('availability', e.target.value)}
                    className="input"
                  >
                    <option value="Remote">عن بعد</option>
                    <option value="On-site">في الموقع</option>
                    <option value="Hybrid">هجين</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">مستوى الخبرة</label>
                  <select
                    value={profile.experience_level}
                    onChange={(e) => handleChange('experience_level', e.target.value)}
                    className="input"
                  >
                    {experienceLevels.map(level => (
                      <option key={level} value={level}>{level}</option>
                    ))}
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">نبذة عنك</label>
                  <textarea
                    value={profile.bio}
                    onChange={(e) => handleChange('bio', e.target.value)}
                    rows={4}
                    className="input"
                    placeholder="اكتب نبذة مختصرة عنك وعن خبرتك..."
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 mb-1">روابط المعرض/البورتفوليو (سطر لكل رابط)</label>
                  <textarea
                    value={profile.portfolio_urls.join('\n')}
                    onChange={(e) => handleChange('portfolio_urls', e.target.value.split('\n').filter(Boolean))}
                    rows={3}
                    className="input"
                    placeholder="https://portfolio.com\nhttps://github.com/username"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Skills Tab */}
          {activeTab === 'skills' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Zap className="h-5 w-5" /> المهارات والكفاءات
                </h3>
                <div className="flex gap-2">
                  <input
                    type="text"
                    placeholder="أضف مهارة جديدة..."
                    className="input w-64"
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), addSkill(e.currentTarget.value), e.currentTarget.value = '')}
                  />
                </div>
              </div>
              
              <div className="flex flex-wrap gap-2">
                {profile.skills.map((skill) => (
                  <span
                    key={skill}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-primary-50 text-primary-700 rounded-full text-sm"
                  >
                    {skill}
                    <button
                      onClick={() => removeSkill(skill)}
                      className="text-primary-500 hover:text-primary-700 p-0.5"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>

              <h3 className="font-semibold text-gray-900 mt-6 flex items-center gap-2">
                <Languages className="h-5 w-5" /> اللغات
              </h3>
              <div className="flex flex-wrap gap-2">
                {profile.languages.map((lang) => (
                  <span
                    key={lang}
                    className="inline-flex items-center gap-1 px-3 py-1 bg-green-50 text-green-700 rounded-full text-sm"
                  >
                    {lang}
                    <button
                      onClick={() => handleChange('languages', profile.languages.filter(l => l !== lang))}
                      className="text-green-500 hover:text-green-700 p-0.5"
                    >
                      ×
                    </button>
                  </span>
                ))}
              </div>
              
              <div className="flex gap-2 pt-4">
                <input
                  type="text"
                  placeholder="أضف لغة..."
                  className="input w-64"
                  onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleChange('languages', [...new Set([...profile.languages, e.currentTarget.value.trim()])]), e.currentTarget.value = '')}
                />
              </div>
            </div>
          )}

          {/* Preferences Tab */}
          {activeTab === 'preferences' && (
            <div className="space-y-6">
              <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                <DollarSign className="h-5 w-5" /> النطاق السعري والتفضيلات
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">أقل سعر بالساعة</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={profile.hourly_rate_range.min}
                    onChange={(e) => handleChange('hourly_rate_range', { ...profile.hourly_rate_range, min: parseFloat(e.target.value) || 0 })}
                    className="input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">أعلى سعر بالساعة</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    value={profile.hourly_rate_range.max}
                    onChange={(e) => handleChange('hourly_rate_range', { ...profile.hourly_rate_range, max: parseFloat(e.target.value) || 0 })}
                    className="input"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">العملة</label>
                  <select
                    value={profile.hourly_rate_range.currency}
                    onChange={(e) => handleChange('hourly_rate_range', { ...profile.hourly_rate_range, currency: e.target.value })}
                    className="input"
                  >
                    {currencies.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="border-t border-gray-100 pt-6">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <CreditCard className="h-5 w-5" /> أنواع الوظائف المفضلة
                </h3>
                <div className="flex flex-wrap gap-3 mt-3">
                  {jobTypes.map(type => (
                    <label key={type} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={profile.preferred_job_types.includes(type)}
                        onChange={(e) => handleChange('preferred_job_types', e.target.checked 
                          ? [...profile.preferred_job_types, type]
                          : profile.preferred_job_types.filter(t => t !== type)
                        )}
                        className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                      />
                      <span className="text-sm capitalize">{type.replace('_', ' ')}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="border-t border-gray-100 pt-6">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Clock className="h-5 w-5" /> ساعات العمل الأسبوعية
                </h3>
                <input
                  type="number"
                  min="1"
                  max="60"
                  value={profile.max_hours_per_week}
                  onChange={(e) => handleChange('max_hours_per_week', parseInt(e.target.value) || 0)}
                  className="input w-32"
                />
              </div>

              <div className="border-t border-gray-100 pt-6">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                  <Shield className="h-5 w-5" /> نقاط القوة
                </h3>
                <div className="flex flex-wrap gap-2">
                  {profile.strengths.map((strength) => (
                    <span
                      key={strength}
                      className="inline-flex items-center gap-1 px-3 py-1 bg-purple-50 text-purple-700 rounded-full text-sm"
                    >
                      {strength}
                      <button
                        onClick={() => handleChange('strengths', profile.strengths.filter(s => s !== strength))}
                        className="text-purple-500 hover:text-purple-700 p-0.5"
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
                <div className="flex gap-2 mt-3">
                  <input
                    type="text"
                    placeholder="أضف نقطة قوة..."
                    className="input w-64"
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleChange('strengths', [...new Set([...profile.strengths, e.currentTarget.value.trim()])]), e.currentTarget.value = '')}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Email & Notifications Tab */}
          {activeTab === 'email' && (
            <div className="space-y-6">
              {/* Email Configuration */}
              <div className="bg-gray-50 rounded-xl p-6 border border-gray-200">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                    <Wifi className="h-5 w-5 text-blue-600" /> إعدادات خادم البريد (SMTP)
                  </h3>
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={emailConfig.enabled}
                      onChange={(e) => handleEmailConfigChange('enabled', e.target.checked)}
                      className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                    />
                    <span className="text-sm text-gray-600">تفعيل الإرسال عبر SMTP</span>
                  </label>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">خادم SMTP</label>
                    <input
                      type="text"
                      value={emailConfig.smtp_host}
                      onChange={(e) => handleEmailConfigChange('smtp_host', e.target.value)}
                      className="input"
                      placeholder="smtp.gmail.com"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">المنفذ</label>
                    <input
                      type="number"
                      value={emailConfig.smtp_port}
                      onChange={(e) => handleEmailConfigChange('smtp_port', parseInt(e.target.value) || 587)}
                      className="input"
                      placeholder="587"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">اسم المستخدم (البريد)</label>
                    <input
                      type="email"
                      value={emailConfig.username}
                      onChange={(e) => handleEmailConfigChange('username', e.target.value)}
                      className="input"
                      placeholder="your-email@gmail.com"
                    />
                  </div>
                  <div className="relative">
                    <label className="block text-sm font-medium text-gray-700 mb-1">كلمة المرور / App Password</label>
                    <div className="relative">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        value={emailConfig.password}
                        onChange={(e) => handleEmailConfigChange('password', e.target.value)}
                        className="input pr-10"
                        placeholder="••••••••"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                      </button>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">استخدم App Password لـ Gmail</p>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">البريد المرسل منه</label>
                    <input
                      type="email"
                      value={emailConfig.from_email}
                      onChange={(e) => handleEmailConfigChange('from_email', e.target.value)}
                      className="input"
                      placeholder="noreply@yourdomain.com"
                    />
                  </div>
                  <div className="flex items-end">
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={emailConfig.use_tls}
                        onChange={(e) => handleEmailConfigChange('use_tls', e.target.checked)}
                        className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                      />
                      <span className="text-sm text-gray-600">استخدام TLS</span>
                    </label>
                  </div>
                </div>
              </div>

              {/* Notification Preferences */}
              <div className="bg-blue-50 rounded-xl p-6 border border-blue-200 mt-6">
                <h3 className="font-semibold text-gray-900 flex items-center gap-2 mb-4">
                  <Bell className="h-5 w-5 text-blue-600" /> تفضيلات الإشعارات
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={notifications.enabled}
                        onChange={(e) => handleNotificationChange('enabled', e.target.checked)}
                        className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                      />
                      <span className="text-sm font-medium text-gray-700">تفعيل الإشعارات البريدية</span>
                    </label>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">البريد الإلكتروني المستلم</label>
                    <input
                      type="email"
                      value={notifications.email}
                      onChange={(e) => handleNotificationChange('email', e.target.value)}
                      className="input"
                      placeholder="your-email@example.com"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4">
                  <label className="flex items-center gap-2 cursor-pointer p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors">
                    <input
                      type="checkbox"
                      checked={notifications.on_scan_complete}
                      onChange={(e) => handleNotificationChange('on_scan_complete', e.target.checked)}
                      className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                    />
                    <div>
                      <p className="text-sm font-medium text-gray-700">اكتمال المسح</p>
                      <p className="text-xs text-gray-500">إشعار عند انتهاء كل مسح تلقائي</p>
                    </div>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors">
                    <input
                      type="checkbox"
                      checked={notifications.on_high_match}
                      onChange={(e) => handleNotificationChange('on_high_match', e.target.checked)}
                      className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                    />
                    <div>
                      <p className="text-sm font-medium text-gray-700">فرص مطابقة عالية</p>
                      <p className="text-xs text-gray-500">تنبيه فوري عند وجود فرصة بدرجة ≥ 75</p>
                    </div>
                  </label>
                  <label className="flex items-center gap-2 cursor-pointer p-3 bg-white rounded-lg border border-gray-200 hover:border-blue-300 transition-colors">
                    <input
                      type="checkbox"
                      checked={notifications.on_new_job}
                      onChange={(e) => handleNotificationChange('on_new_job', e.target.checked)}
                      className="h-4 w-4 text-primary-600 rounded border-gray-300 focus:ring-primary-500"
                    />
                    <div>
                      <p className="text-sm font-medium text-gray-700">وظائف جديدة</p>
                      <p className="text-xs text-gray-500">إشعار لكل وظيفة جديدة تُضاف</p>
                    </div>
                  </label>
                </div>

                <div className="flex items-center gap-3 mt-4 pt-4 border-t border-blue-100">
                  <input
                    type="email"
                    value={notifications.email}
                    onChange={(e) => handleNotificationChange('email', e.target.value)}
                    className="input flex-1"
                    placeholder="بريد الإشعارات (مثال: islam230366qw@gmail.com)"
                  />
                  <button
                    onClick={handleTestEmail}
                    disabled={testingEmail}
                    className="btn btn-primary flex items-center gap-2 whitespace-nowrap"
                  >
                    {testingEmail ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        جاري الإرسال...
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4" />
                        إرسال بريد اختباري
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          )}

        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-gray-100 bg-gray-50 flex justify-end gap-3 sticky bottom-0">
          <button onClick={onClose} className="btn btn-secondary">
            إلغاء
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className={cn('btn btn-primary', saving && 'opacity-50')}
          >
            {saving ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                جاري الحفظ...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                حفظ جميع الإعدادات
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
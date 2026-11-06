#include <glib.h>
#include <string.h>
#include "greeterconfiguration.h"
typedef void LightDMGreeter;
#define GTK_WIDGET(x) (x)
#define GTK_MESSAGE_ERROR 1
#define LIGHTDM_MESSAGE_TYPE_ERROR 1
#define _(x) (x)
static gboolean cancelling,prompted,prompt_active,authenticated,opt_in;
static gpointer password_entry,user_combo,info_bar;
static GSList *pending_questions;
static int sessions,cancellations,retries;
static void gtk_entry_set_text(gpointer p,const char *s){(void)p;(void)s;}
static void gtk_widget_hide(gpointer p){(void)p;}
static void gtk_widget_grab_focus(gpointer p){(void)p;}
static void cancel_authentication(void){cancellations++;}
static void pam_message_finalize(gpointer p){g_free(p);}
static gboolean lightdm_greeter_get_is_authenticated(LightDMGreeter *p){(void)p;return authenticated;}
static const char *lightdm_greeter_get_authentication_user(LightDMGreeter *p){(void)p;return "test-user";}
static void start_session(void){sessions++;}
static void start_authentication(const char *s){(void)s;retries++;}
static gboolean message_label_is_empty(void){return TRUE;}
static int gtk_info_bar_get_message_type(gpointer p){(void)p;return GTK_MESSAGE_ERROR;}
static void set_message_label(int k,const char *s){(void)k;(void)s;}
gboolean config_get_bool(const char *group,const char *key,gboolean fallback){g_assert_null(group);g_assert_cmpstr(key,==,CONFIG_KEY_START_ON_AUTH_SUCCESS);g_assert_false(fallback);return opt_in;}
#include "authentication-complete.inc"
static void run_case(gboolean auth,gboolean prompt,gboolean enabled,gboolean cancel,int expected){
 authenticated=auth;prompted=prompt;opt_in=enabled;cancelling=cancel;sessions=0;cancellations=0;retries=0;prompt_active=TRUE;
 authentication_complete_cb(NULL);
 g_assert_cmpint(sessions,==,expected);g_assert_false(prompt_active);
 if(cancel)g_assert_cmpint(cancellations,==,1);
 if(!auth&&prompt&&!cancel)g_assert_cmpint(retries,==,1);
}
int main(void){
 run_case(TRUE,FALSE,TRUE,FALSE,1);
 run_case(TRUE,FALSE,FALSE,FALSE,0);
 run_case(TRUE,TRUE,FALSE,FALSE,1);
 run_case(FALSE,FALSE,TRUE,FALSE,0);
 run_case(FALSE,TRUE,TRUE,FALSE,0);
 run_case(TRUE,FALSE,TRUE,TRUE,0);
 run_case(FALSE,FALSE,TRUE,TRUE,0);
 g_print("PASS: 7 authentication completion cases; failed and cancelled authentication never starts a session.\n");return 0;
}

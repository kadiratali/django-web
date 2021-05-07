from flask import Flask,render_template,flash,redirect,url_for,session,logging,request
from flask_mysqldb import MySQL
from wtforms import Form,StringField,TextAreaField,PasswordField,validators
from passlib.hash import sha256_crypt
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("Bu sayfayı görüntülemek için lütfen giriş yapınız","danger")
            return redirect(url_for("login"))
    return decorated_function


class RegisterForm(Form):
    name = StringField("İsim Soyisim",validators=[validators.Length(min=4,max=25)])
    username = StringField("Kullanıcı adı",validators=[validators.Length(min=5,max=25)])
    email = StringField("Email",validators=[validators.Email(message="Lütfen Geçerli Bir Email Adresi Girin...")])
    password = PasswordField("Şifre",validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin"),
        validators.EqualTo(fieldname="confirm",message="Parolanız uyuşmuyor...")
    ])
    confirm = PasswordField("Parola Doğrula")

class LoginForm(Form):
    username = StringField("Kullanıcı Adı")
    password = PasswordField("Parola")


class ArticleForm(Form):
    title = StringField("Makale Başlığı",validators=[validators.Length(min=5,max=100)])
    content = TextAreaField("Makale İçeriği",validators=[validators.Length(min = 10)])


app = Flask(__name__)
app.secret_key="ybbilimi"

app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "geziblogu"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

@app.route("/")
def index():

    return render_template("index.html")
    
@app.route("/about")
def about():

    return render_template("about.html")

@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    result=""

    if session["username"] == 'admin':
        sorgu = "Select * From articles"
        result=cursor.execute(sorgu)
    else:
        sorgu = "Select * From articles where author = %s"
        result = cursor.execute(sorgu,(session["username"],))
        
    if result>0:
        articl = cursor.fetchall()
        return render_template("dashboard.html",articl = articl)
    else:
        return render_template("dashboard.html")
#Kayıt Olma

@app.route("/register",methods = ["GET","POST"])
def register():
    form = RegisterForm(request.form)
    
    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)

        cursor = mysql.connection.cursor()

        sorgu = "Insert into users(name,email,username,password) VALUES(%s,%s,%s,%s)"

        cursor.execute(sorgu,(name,email,username,password))

        mysql.connection.commit()

        cursor.close()
        flash("Basarıyla Kayıt Oldunuz...","success")

        return redirect(url_for("login"))
        
    return render_template("register.html",form=form)

@app.route("/login",methods=["GET","POST"])
def login():

    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data

        cursor = mysql.connection.cursor()

        sorgu = "Select * From users where username = %s"

        result=cursor.execute(sorgu,(username,))

        if result>0:
            data = cursor.fetchone()
            real_pasword = data["password"]
            if sha256_crypt.verify(password_entered,real_pasword):
                flash("Giriş Başarılı.","success")
                session["logged_in"] = True
                session["username"] = username
                return redirect(url_for("index"))
            else:
                flash("Parolanızı Yanlış Girdiniz!","danger")
                return redirect(url_for("login"))

        else:
            flash("Böyle Bir Kullanıcı Adı Bulunmuyor...","danger")
            return redirect(url_for("login"))

    return render_template("login.html",form=form)

@app.route("/article/<string:id>",methods=["GET","POST"])
def article(id):
    if request.method == "POST" and len(request.form.get("comment")) > 0 :
        print(len(request.form.get("comment")))
        comment = request.form.get("comment")
        cursor = mysql.connection.cursor()
        sorgu = "Insert into comment(article_id,author,message) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(id,session["username"],comment))
        mysql.connection.commit()
        cursor.close()
    
    cursor1 = mysql.connection.cursor()
    sorgu1 = "Select * From comment where article_id = %s"
    cursor1.execute(sorgu1,(id,))
    artic = cursor1.fetchall()

    cursor = mysql.connection.cursor()
    sorgu = "Select * From articles where id = %s"
    result = cursor.execute(sorgu,(id,))
    if result>0:
        article = cursor.fetchone()
        return render_template("article.html",article=article,artic=artic)
    else:
        return render_template("article.html")
@app.route("/logout")
def logout():
    session.clear()

    return redirect(url_for("index"))

@app.route("/addarticle",methods = ["GET","POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate():
        title = form.title.data
        content = form.content.data

        cursor = mysql.connection.cursor()
        sorgu = "Insert into articles(title,author,content) VALUES(%s,%s,%s)"
        cursor.execute(sorgu,(title,session["username"],content))
        mysql.connection.commit()
        cursor.close()

        flash("Makale Başarıyla EKlendi","success")

        return redirect(url_for("dashboard"))

    return render_template("addarticle.html",form=form)

@app.route("/articles")
def articles():

    cursor = mysql.connection.cursor()

    sorgu = "Select * From articles"

    result=cursor.execute(sorgu)
    
    if result>0:

        datalar = cursor.fetchall()
        return render_template("articles.html",datalar = datalar)
    
    return render_template("articles.html")
@app.route("/delete/<string:id>")
@login_required
def delete(id):

    if session["username"] == 'admin':
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where id= %s"
        result = cursor.execute(sorgu,(id,))

        if result>0:
            sorgu2 = "Delete from articles where id = %s"

            cursor.execute(sorgu2,(id,))

            mysql.connection.commit()
            return redirect(url_for("dashboard"))
    else:
        flash("Böyle bir makale yok veya erişim izniniz yok.","danger")
        return redirect(url_for("index"))

@app.route("/update/<string:id>",methods = ["GET","POST"])
@login_required
def update(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where author = %s and id= %s"
        result = cursor.execute(sorgu,(session["username"],id))
        if result>0:
            article=cursor.fetchone()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("update.html",form=form)
        else:
            flash("Böyle bir makale yok veya bu işleme yetkiniz yok.","danger")
            return redirect(url_for("index"))
    else:
        form = ArticleForm(request.form)
        if request.method == "POST" and form.validate():
            newtitle = form.title.data
            newcontent = form.content.data

            cursor = mysql.connection.cursor()
            sorgu2 = "Update articles Set title = %s,content = %s where id=%s"
            cursor.execute(sorgu2,(newtitle,newcontent,id))
            mysql.connection.commit()

            flash("Makale Başarıyla Güncellendi","success")

            return redirect(url_for("dashboard"))

        return render_template("update.html",form=form)
        
@app.route("/search",methods = ["GET","POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")
        cursor = mysql.connection.cursor()
        sorgu = "Select * from articles where title like '%" + keyword + "%'"
        result = cursor.execute(sorgu)
        if result == 0:
            flash("Aranan kelimeye uygun makale bulunamadı...","warning")
            return redirect(url_for("articles"))
        else:
            datalar = cursor.fetchall()
            return render_template("articles.html",datalar=datalar)

if __name__=="__main__":
    app.run(debug=True)

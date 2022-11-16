import pandas as pd
import streamlit as st
import os.path

from github import Github
from github import InputGitTreeElement
from datetime import datetime

import cryptography
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt

import secrets
import base64
import getpass

from createWebformDict import *

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.mime.application import MIMEApplication

def send_email(sender, password, receiver, smtp_server, smtp_port, email_message, subject, attachment=None):

    message = MIMEMultipart()
    message['To'] = Header(receiver)
    message['From']  = Header(sender)
    message['Subject'] = Header(subject)
    message.attach(MIMEText(email_message,'plain', 'utf-8'))
    
    if attachment:
    
        att = MIMEApplication(attachment.read(), _subtype="txt")
        att.add_header('Content-Disposition', 'attachment', filename=attachment.name)
        message.attach(att)
        server = smtplib.SMTP(smtp_server, smtp_port)
        print('server',server)
        server.starttls()
        server.ehlo()
        server.login(sender, password)
        text = message.as_string()
        server.sendmail(sender, receiver, text)
        server.quit()

    return

def generate_salt(size=16):
    """Generate the salt used for key derivation, 
    `size` is the length of the salt to generate"""
    return secrets.token_bytes(size)
    
def derive_key(salt, password):
    """Derive the key from the `password` using the passed `salt`"""
    kdf = Scrypt(salt=salt, length=32, n=2**14, r=8, p=1)
    return kdf.derive(password.encode())
    
def load_salt():
    # load salt from salt.salt file
    return open("salt.salt", "rb").read()
    
def generate_key(password, salt_size=16, load_existing_salt=False, save_salt=True):
    """
    Generates a key from a `password` and the salt.
    If `load_existing_salt` is True, it'll load the salt from a file
    in the current directory called "salt.salt".
    If `save_salt` is True, then it will generate a new salt
    and save it to "salt.salt"
    """
    if load_existing_salt:
        # load existing salt
        salt = load_salt()
    elif save_salt:
        # generate new salt and save it
        salt = generate_salt(salt_size)
        with open("salt.salt", "wb") as salt_file:
            salt_file.write(salt)
    # generate the key from the salt and the password
    derived_key = derive_key(salt, password)
    # encode it using Base 64 and return it
    return base64.urlsafe_b64encode(derived_key)            

def encrypt(filename, key):
    """
    Given a filename (str) and key (bytes), it encrypts the file and write it
    """
    f = Fernet(key)
    with open(filename, "rb") as file:
        # read all file data
        file_data = file.read()
    # encrypt data
    encrypted_data = f.encrypt(file_data)
    # write the encrypted file
    with open(filename, "wb") as file:
        file.write(encrypted_data)

def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

def pushToGithub(Repository,df_new,input_dir,csv_file,quest_type,datarepo):
    
    if datarepo == 'github':

        g = Github(st.secrets["github_token"])
    
    elif datarepo == 'local_github':
    
        g = Github(user,github_token)
    
    
    repo = g.get_user().get_repo(Repository)

    now = datetime.now()
    dt_string = now.strftime("%Y_%m_%d_%H_%M_%S")

    # Upload to github
    git_prefix = input_dir+'/'+ quest_type+'/'
    
    git_file = git_prefix +csv_file.replace('.csv','_')+dt_string+'_Output.csv'
    df2 = df_new.to_csv(sep=',', index=False)

    try:

        repo.create_file(git_file, "committing files", df2, branch="main")
        st.write(git_file + ' CREATED')
        print(git_file + ' CREATED')
        
    except:
    
        print('Problem committing file')    
   
    return git_file

def saveAnswer(df_new,input_dir,csv_file,quest_type):

    output_dir = input_dir+'/'+ quest_type
    # Check whether the specified output path exists or not
    isExist = os.path.exists(output_dir)

    if not isExist:

        # Create a new directory because it does not exist
        os.makedirs(output_dir)
        print('The new directory ' + output_dir + ' is created!')
    
    now = datetime.now()
    dt_string = now.strftime("%Y_%m_%d_%H_%M_%S")

    # Local save
    save_prefix = output_dir + '/'
    
    save_file = save_prefix +csv_file.replace('.csv','_')+dt_string+'_Output.csv'
    # save_file = csv_file.replace('.csv','_')+dt_string+'_Output.csv'

    df_new.to_csv(save_file,sep=',', index=False)

    st.write(save_file + ' SAVED')
    
    return save_file

def check_form(qst,idxs,ans,units,minVals,maxVals,idx_list,idxMins,idxMaxs,sum50s):

    print(ans[0:3])

    n_qst = int((len(qst)-2)/3)
    
    check_flag = True

    for i in range(n_qst):
    
        if idxs[i] in idx_list:
                    
            idx = 3+i*3
        
            if ( ',' in ans[idx] ):
                st.write('Please remove comma')
                st.write(qst[idx],ans[idx])
                check_flag = False
        
            try:
                float(ans[idx])
            except ValueError:
                st.write('Non numeric answer')
                st.write(qst[idx],ans[idx])
                check_flag = False
            
            try:
                float(ans[idx+1])
            except ValueError:
                st.write('Non numeric answer')
                st.write(qst[idx+1],ans[idx+1])
                check_flag = False
            
            try:
                float(ans[idx+2])
            except ValueError:
                st.write('Non numeric answer')
                st.write(qst[idx+2],ans[idx+2])
                check_flag = False
            
            if check_flag:    
            
                if float(ans[idx]) >= float(ans[idx+1]):
        
                    st.write('Error. '+qst[idx]+' >= '+qst[idx+1])            
                    check_flag = False
            
                if float(ans[idx+1]) >= float(ans[idx+2]):
        
                    st.write('Error. '+qst[idx+1]+' >= '+qst[idx+2])            
                    check_flag = False
            
                if float(ans[idx])<= minVals[i] or float(ans[idx])>= maxVals[i]:
                
                    st.write('Error. '+qst[idx]+':'+str(ans[idx]))
                    st.write('The answer must be a value >'+str(minVals[i])+' and  <'+str(maxVals[i]))
                    check_flag = False
            
                if float(ans[idx+1])<= minVals[i] or float(ans[idx+1])>= maxVals[i]:
                
                    st.write('Error. '+qst[idx+1]+':'+str(ans[idx+1]))
                    st.write('The answer must be a value  >'+str(minVals[i])+' and <'+str(maxVals[i]))
                    check_flag = False
            
                if float(ans[idx+2])<= minVals[i] or float(ans[idx+2])>= maxVals[i]:
                    
                    st.write('Error. '+qst[idx+2]+':'+str(ans[idx+2]))
                    st.write('The answer must be a value >'+str(minVals[i])+' and <'+str(maxVals[i]) )
                    check_flag = False
                    
                if (idxMins[i] < idxMaxs[i]):
                
                    sum50check = 0.0
                    
                    for ii in range(idxMins[i]-1,idxMaxs[i]):
                    
                        sum50check += float(ans[4+ii*3])
                        
                    if float(sum50s[i] != sum50check):  
                      
                        st.write('Error in sum of 50%iles for questions from ',str(idxMins[i]),' to ',str(idxMaxs[i]))
                        st.write('The sum should be '+str(sum50s[i]))
                        check_flag = False
                    
                    

    return check_flag       

def main():

    hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True) 

    st.title("Elicitation form")
    
    try: 
    
        from createWebformDict import datarepo
        
    except ImportError:
    
        datarepo = 'local'  
        
    print('Data repository:',datarepo)  
    
    if ( datarepo == 'github' ) or ( datarepo == 'local_github' ):
    
        try: 
    
            from createWebformDict import Repository
            
        
        except ImportError:
    
            print('Please add Repository')        

    try:
    
        from createWebformDict import encrypted
                
    except ImportError:
    
        encrypted = False
        
    print('Encrypting of data:',encrypted)    
        
    if encrypted:
    
        if ( datarepo == 'local' ) or ( datarepo == 'local_github' ):
        
            password = getpass.getpass("Enter the password for encryption: ")
            key = generate_key(password, load_existing_salt=False)
       
    # check if the pdf supporting file is defined and if it exists
    try:
    
        from createWebformDict import companion_document
        
        pdf_doc = './'+input_dir+'/'+ companion_document
        # Check whether the specified output path exists or not
        isExists = os.path.exists(pdf_doc)

    except ImportError:
        
        isExists = False
  
    if isExists:  
    
        with open(pdf_doc, "rb") as pdf_file:
        
            PDFbyte = pdf_file.read()

        st.download_button(label="Download PDF Questionnaire", 
            data=PDFbyte,
            file_name=companion_document,
            mime='application/octet-stream')

    # check if supplemetry docs are defined and if the files exists
    try:
    
        from createWebformDict import supplementary_documents
        
        isExists = True

    except ImportError:
        
        isExists = False
  
    if isExists:  
    
        for doc in supplementary_documents:
        
            pdf_doc = './'+input_dir+'/'+ doc
            
            isExists = os.path.exists(pdf_doc)
    
            if isExists:
    
                with open(pdf_doc, "rb") as pdf_file:
        
                    PDFbyte = pdf_file.read()

                st.download_button(label="Download "+doc, 
                    data=PDFbyte,
                    file_name=doc,
                    mime='application/octet-stream')
    
    # read the questionnaire to a pandas dataframe	
    df = pd.read_csv('./'+input_dir+'/'+csv_file,header=0,index_col=0)
 
    if quest_type == 'seed':
        
        try:
    
            from createWebformDict import seed_list
            print('seed_list read',seed_list)
            idx_list = seed_list
    
        except ImportError:
    
            print('ImportError')    
            idx_list = list(df.index)
            
    if quest_type == 'target':
        
        try:
    
            from createWebformDict import target_list
            print('seed_list read',target_list)
            idx_list = target_list
    
        except ImportError:
    
            print('ImportError')    
            idx_list = list(df.index)            
            
    if len(idx_list) == 0:
    
        idx_list = list(df.index)
                
    data_top = df.head()
    
    langs = []
    
    for head in data_top:
    
        if 'LONG Q' in head:
        
            string = head.replace('LONG Q','')
            string2 = string.replace('_','')
            
            langs.append(string2)
            
    print('langs',langs)        
             
    if (len(langs)>1):
    
        options = langs
        lang_index = st.selectbox("Language", range(len(options)), format_func=lambda x: options[x])
        print('lang_index',lang_index)
        language = options[lang_index]
        index_list = [0,1,lang_index+2]+list(range(len(langs)+2,len(langs)+12))
        print('language',language) 
        
    else:
     
        lang_index = 0
        language = ''
        index_list = list(range(0,13))
               
    # print('index_list',index_list)    
    
    output_file = csv_file.replace('.csv','_NEW.csv')

    pctls = [5,50,95]

    form2 = st.form(key='form2')
    
    ans = []

    qst = ["First Name"]    
    ans.append(form2.text_input(qst[-1]))
    
    qst.append("Last Name")
    ans.append(form2.text_input(qst[-1]))
    
    qst.append("Email address")
    ans.append(form2.text_input(qst[-1]))

        
    idxs = []
    units = []
    minVals = []
    maxVals = []
    
    idxMins = []
    idxMaxs = []
    sum50s = []
        
    for i in df.itertuples():
    
        idx,shortQ,longQ,unit,scale,minVal,maxVal,realization,question,idxMin,idxMax,sum50,image = [i[j] for j in index_list]
        # print(idx,question,question == quest_type)
        minVal = float(minVal)
        maxVal = float(maxVal)
        
        if ( question == quest_type):

            units.append(unit)
            idxs.append(idx)
            
            if minVal.is_integer():
            
                minVal = int(minVal)
                    
            if maxVal.is_integer():
            
                maxVal = int(maxVal)

            minVals.append(minVal)
            maxVals.append(maxVal)
            
            sum50 = float(sum50)     
                
            idxMins.append(idxMin)
            idxMaxs.append(idxMax)
            sum50s.append(sum50)
            
            # print('idx',idx,idx in idx_list)
            
            if (idx in idx_list):
            
                form2.markdown("""___""")
                # print(idx,qst,unit,scale)
                if quest_type == 'target':
                
                    form2.header('TQ'+str(idx)+'. '+shortQ)
                    
                else:

                    form2.header('SQ'+str(idx)+'. '+shortQ)
            
                if (not pd.isnull(image)):
                    imagefile = './'+input_dir+'/images/'+str(image)
                    if os.path.exists(imagefile):  
                        form2.image('./'+input_dir+'/images/'+str(image))
                        
                if idxMin<idxMax:
                
                    longQ_NB = "**N.B.** *The sum of 50%iles for questions "+str(idxMin)+"-"+str(idxMax)+" have to sum to "+str(sum50)+".*"        
                    form2.markdown(longQ)
                    form2.markdown(longQ_NB)
                
                else:    
        
                    form2.markdown(longQ)
        
            j=0
            for pct in pctls:
                j+=1
            
                qst.append(shortQ+' - '+str(int(pct))+'%ile ('+str(minVal)+';'+str(maxVal)+')'+' ['+unit+']')
    
                if (idx in idx_list):
                
                    ans.append(form2.text_input(qst[-1]))
                    
                else:
                
                    ans.append('')

   
    form2.markdown("""___""")
                    
    agree_text = "By sending this form and clicking the option “I AGREE”, you hereby consent to the processing of your given personal data (first name, last name and email address) voluntarily provided. These data are used for the only purpose of associating the asnwers of the seed question to those of the target questions, and to communicate with the participant only for matters related to the expert elicitation. In accordance with the EU GDPR, your personal data will be stored on a privite Github repository (https://github.com/security) for as long as is necessary for the purposes for which the personal data are processed." 
    
    agree = form2.checkbox('I AGREE')
    
    form2.write(agree_text)

    form2.markdown("""___""")

    zip_iterator = zip(qst,ans)
    data = dict(zip_iterator)
    df_download = pd.DataFrame([ans],columns=qst)
    csv = convert_df(df_download)

    now = datetime.now()
    dt_string = now.strftime("%Y_%m_%d_%H:%M:%S")

    file_download = 'myans_'+dt_string+'.csv'

    dwnl = st.download_button(
        label="Download answers as CSV",
        data=csv,
        file_name=file_download,
        mime='text/csv',
    )
                
    submit_button2 = form2.form_submit_button("Submit")
    
        
    if submit_button2:
    
        check_flag = check_form(qst,idxs,ans,units,minVals,maxVals,idx_list,idxMins,idxMaxs,sum50s)
        
        print('check_flag',check_flag)
        
        if not agree:
        
            st.write('Please agree to the terms above')
                               
        if check_flag and agree:
    
            st.write('Thank you '+ans[0]+' '+ans[1] )
            st.write('Please download a copy of your answers and keep the file.')
        
            zip_iterator = zip(qst,ans)
            data = dict(zip_iterator)
            df_new = pd.DataFrame([ans],columns=qst)
            
            if encrypted:
            
                f = Fernet(key)
                df_new = f.encrypt(df_new)
                        
            if datarepo == 'github':
            
                print('Before pushing file to Gihub')
                save_file = pushToGithub(Repository,df_new,input_dir,csv_file,quest_type,datarepo)
                save_file = './'+save_file
                print('After pushing file to Gihub')
                
            else:
            
                print('Before saving file')
                save_file = saveAnswer(df_new,input_dir,csv_file,quest_type)
                print('After saving file')
            
            if confirmation_email:
            
                if datarepo == 'github':
                
                    SENDER_ADDRESS = st.secrets["SENDER_ADDRESS"]
                    SENDER_PASSWORD = st.secrets["SENDER_PASSWORD"]
                    SENDER_NAME = st.secrets["SENDER_NAME"]
                    SMTP_SERVER_ADDRESS = st.secrets["SMTP_SERVER_ADDRESS"]
                    PORT = st.secrets["PORT"]
                                
                email = ans[2]
                message = 'Dear xxx,\nThank you for filling in the questionaire.\nYou can find your answers attached to the email.\nKind regards,\n'+SENDER_NAME
                subject = 'Elicitation confirmation'
            
            
                with open(save_file, "rb") as attachment:
                
                    try:

                        send_email(sender=SENDER_ADDRESS, password=SENDER_PASSWORD, receiver=email, smtp_server=SMTP_SERVER_ADDRESS, smtp_port=PORT, email_message=message, subject=subject, attachment=attachment) 
                        
                    except:
                    
                        st.write('Problem sending the confirmation email')
                        print('Problem sending the confirmation email')    
    
                
                
        
if __name__ == '__main__':
	main()            

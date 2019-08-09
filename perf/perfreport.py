from pymongo import MongoClient
from flask import render_template, request, url_for, redirect
import csv
import json
import configparser
from distutils.util import strtobool

config = configparser.ConfigParser()
config.read("config.ini")
#file level variable block starts

# Below paramters reads data from config.ini file
mongo_ip = config.get("mongoParams", "mongo_ip")
if mongo_ip == '' :
	mongo_ip = 'mongo_perf'
		
mongo_port = config.get("mongoParams", "mongo_port")
if mongo_port == '' :
	mongo_port = 27017
	
db_name = config.get("mongoParams", "db_name")
if db_name == '' :
	db_name = 'perf_db'
	
db_collection = config.get("mongoParams", "db_collection")
if db_collection == '' :
	db_collection = 'perf_coll'

CLIENT = MongoClient(mongo_ip,int(mongo_port))
MONGO_PERF_DB = CLIENT[db_name]
MONGO_PERF_COLLECTION= MONGO_PERF_DB[db_collection]

IS_DEV_MODE = strtobool(config.get("devMode", "IS_DEV_MODE"))
#file level variable block ends


def perf_csv_parser(filename, release, build, collection, date, application):
    """
    This api is used to parse csv file data and insert data to mongodb
    :param filename:
    :param release:
    :param build:
    :param collection:
    :param date:
    :param application:
    :return:
    """
    try :
        reader = csv.DictReader(open(filename))
        query = {'Release': release, 'Build': build, 'date': date, 'Application_Type' : application}
        result = {}
        for row in reader:
            key = row.pop('sampler_label')
            result[key] = row
        query['Result'] = result

        top_three_report_error_percent = {}
        exp1 = dict(sorted(result.items(), key=lambda x: float(x[1]['aggregate_report_90%_line']), reverse=True)[:3])
        for k, v in exp1.items():
            top_three_report_error_percent[k] = str(v['aggregate_report_error%'])

        highlights = {'aggregate_report_count': result['TOTAL']['aggregate_report_count'],
                      'average': result['TOTAL']['average'],
                      'aggregate_report_median': result['TOTAL']['aggregate_report_median'],
                      'aggregate_report_90_percent_line': result['TOTAL']['aggregate_report_90%_line'],
                      'aggregate_report_error_percent': str(result['TOTAL']['aggregate_report_error%']),
                      'aggregate_report_rate': str(round(float(result['TOTAL']['aggregate_report_rate']), 2)),
                      'top_three_report_error_percent': top_three_report_error_percent}
        query['Highlights'] = highlights
        collection.insert_one(query)

    except Exception as e:
        return "Error occured while parsing csv .Error is " + e.__str__()
    return True


def importperfresult():
    return render_template('import_perf_result.html', title="Import Perf Results", is_dev_mode=IS_DEV_MODE)


def upload_file():
    '''
    This api is used to fetch form data and store the uploaded csv file in mongo db .
    :return:
    '''
    try :
        if request.method == 'POST':
            f = request.files['file']
            f.save(f.filename)
            perf_csv_parser(f.filename, request.form['release'], request.form['build'],
                            MONGO_PERF_COLLECTION, request.form['date'],request.form['Application_Type'])
    except Exception as e:
            return "Error occured while uploading file .Error is " + e.__str__()
    return 'Data imported into Mongo DB'


def perf_compare_ui():

    '''
    This api fetches the required data of releases from mongo db and renders html template form.
    :return:
    '''
    try :
        release_list = {'Jboss':['--None--'],'Wildfly' : ['--None--']}
        if request.method == 'GET':
            try:
                releases = (MONGO_PERF_COLLECTION.find({}, {'Release': 1,'Application_Type':4}))
                for value in releases:
                                    if value['Application_Type']=='Jboss' :
                                        release_list['Jboss'].append(value['Release'])
                                    else:
                                        release_list['Wildfly'].append(value['Release'])
            except Exception as e:
                return "Error occured while fetching data for releases .Error is "+e.__str__()
            return render_template('perf_compare_ui.html', data=release_list, title='Perf Compare Result', is_dev_mode=IS_DEV_MODE)
        else:
            formdata = request.form
            base_rel = formdata['base_rel']
            curr_rel = formdata['curr_rel']
            perfreporturl = url_for('perfcompare', baseline_release=base_rel, current_release=curr_rel)
            if not IS_DEV_MODE:
                perfreporturl = "/ms-perfcompare" + perfreporturl
            
            return redirect(perfreporturl)
    except Exception as e:
        return "Error occured while rendering perf compare ui html page .Error is " + e.__str__()


def perf_compare(baseline_release, current_release):
    '''
    This service is used  to get performance results comparison between baseline and current release
    :param baseline_release:2.5.0
    :param current_release:4.1.0_32
    :return:
    '''

    try :

        if baseline_release==current_release :

            return  "<html>Cannot compare same build performance result.Please select two different build.</html>"
        try:
            modules_base = MONGO_PERF_COLLECTION.find_one({'Release': baseline_release})['Result']
            application_type = MONGO_PERF_COLLECTION.find_one({'Release': baseline_release})['Application_Type']
        except Exception as e:
            return "Error occured while fetching data for baseline release " +baseline_release + " .Error is "+e.__str__()
        try:
            modules_current = MONGO_PERF_COLLECTION.find_one({'Release': current_release})['Result']
        except Exception as e:
            return "Error occured while fetching data for baseline release " +current_release + " .Error is "+e.__str__()

        perfcompareui = url_for('perfcompareui')
        if not IS_DEV_MODE:
            perfcompareui = "/ms-perfcompare" + perfcompareui


    except Exception as e:
        return "Error occured while rendering perf results for two different releases .Error is " + e.__str__()

    return render_template('index_sort.html', title='Sorted Perf Report', Application_Type=application_type,
                           modules_base=modules_base, modules_current=modules_current, baseline=baseline_release,
                           current=current_release, backurl=perfcompareui)


def perf_compare_json_report():
    '''
    This API is used to return perf compare result in JSON format
    {"success": "true", "data": {"perf": {"Current_Release": "4.0.0_42", "Baseline_Release": "2.5.0", "result": [["Modules", "Baseline Release Value (2.5.0)", "Current Release Value (4.0.0_42)", "Precent Change", "Status"], ["Search Item to trace", 49.0, 45.0, -8.16326530612245, "Pass"]]}}, "error": {}}
    :return:
    '''
    req_data = request.get_json()
    errordata = {}
    if None == req_data:
        errordata["statuscode"] = 404
        errordata["errormsg"] = "NULL request."
        return builderrorresponse(errordata)

    if None == req_data['data']['baseline_release']:
        errordata["statuscode"] = 404
        errordata["errormsg"] = "baseline_release not found in request."
        return builderrorresponse(errordata)

    if None == req_data['data']['current_release']:
        errordata["statuscode"] = 404
        errordata["errormsg"] = "current_release not found in request."
        return builderrorresponse(errordata)

    baseline_release = req_data['data']['baseline_release']
    current_release = req_data['data']['current_release']
    try:
        modules_base = MONGO_PERF_COLLECTION.find_one({'Release': baseline_release})['Result']
    except Exception as e:
        errordata["statuscode"] = 404
        errordata["errormsg"] = "Error occured while fetching data for baseline release " + baseline_release + " .Error is " + e.__str__()
        return builderrorresponse(errordata)
    try:
        modules_current = MONGO_PERF_COLLECTION.find_one({'Release': current_release})['Result']
    except Exception as e:
        errordata["statuscode"] = 400
        errordata["errormsg"] = "Error occured while fetching data for baseline release " + current_release + " .Error is " + e.__str__()
        return builderrorresponse(errordata)

    returndata = {}
    data={}
    data['Current_Release'] = current_release
    data['Baseline_Release'] = baseline_release
    data['result'] = [['Modules', '90 percentile (' + baseline_release + ')','No of times script executed(' + baseline_release + ')' ,'90 percentile (' + current_release + ')','No of times script executed(' + current_release + ')', 'Precent Change', 'Status']]
    returndata['perf'] = data
    all_base_items = modules_base.items()

    for baseline_item in all_base_items:
        module_name = baseline_item[0]
        baseline_module_data = baseline_item[1]
        current_module_data = modules_current[module_name]
        aggregate_report_90_percentile_baseline = float(baseline_module_data['aggregate_report_90%_line'])
        aggregate_report_count_baseline = float(baseline_module_data['aggregate_report_count'])
        aggregate_report_90_percentile_current = float(current_module_data['aggregate_report_90%_line'])
        aggregate_report_count_current = float(current_module_data['aggregate_report_count'])
        percent_deviation = ((aggregate_report_90_percentile_current - aggregate_report_90_percentile_baseline)/aggregate_report_90_percentile_baseline) * 100
        if aggregate_report_90_percentile_current < (1.05 * aggregate_report_90_percentile_baseline):
            status = "Pass"
        else:
            status = "Fail"
        data['result'] += [[module_name, aggregate_report_90_percentile_baseline,aggregate_report_count_baseline, aggregate_report_90_percentile_current,aggregate_report_count_current, percent_deviation, status]]
    return getsuccessresponse(returndata)


def getsuccessresponse(data):
    returndata = {}
    returndata["success"] = "true"
    returndata["data"] = data
    returndata["error"] = {}
    return json.dumps(returndata)


def builderrorresponse(data):
    returndata = {}
    returndata["success"] = "false"
    returndata["data"] = {}
    returndata["error"] = data
    return json.dumps(returndata)
